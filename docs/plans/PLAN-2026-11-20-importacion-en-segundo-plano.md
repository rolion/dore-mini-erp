# PLAN-2026-11-20-importacion-en-segundo-plano (v1)

**Task:** TASK-importacion-en-segundo-plano · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** `docs/design/DDR-importacion-en-segundo-plano-progreso-de-la-importacion.md` · `docs/adr/ADR-importacion-en-segundo-plano-cola-en-base-de-datos-y-worker.md`

## Objective
Que ejecutar una importación de ventas no dependa del timeout de la petición: se encola, un worker propio la procesa venta a venta y la persona ve el avance (o vuelve después). Elimina el 500 por `SystemExit` de Gunicorn.

## Context
Ver TASK. Reemplaza el punto «ejecución síncrona dentro de la petición» de `ADR-cargar-ventas-desde-archivo-ejecucion-por-venta-e-idempotencia`; el resto (transacción por venta, idempotencia, vista previa sin escritura) no cambia.

# Specification

## Domain context
Bounded context `data_import` (único afectado). Consume por fachadas los mismos módulos que hoy; no se añaden dependencias entre módulos.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Corrida (`ImportRun`) | Un archivo subido con mapeo, opciones y resultado | `models.py:7` |
| En cola (`QUEUED`) | Confirmada por la persona, aún sin worker | nuevo |
| En curso (`RUNNING`) | Un worker la está procesando (con latido) | `models.py:12` |
| Worker | Proceso `run_import_worker` que ejecuta corridas en cola | nuevo |

## Current behavior
`RunExecuteView.post` carga todo en la petición (`api/views.py:125-140`); >30 s ⇒ Gunicorn aborta el worker (500) y la corrida queda `RUNNING` hasta 15 min sin latido.

## Expected behavior
`execute` valida y responde 202 enseguida con la corrida `QUEUED`; el worker la carga y la deja `COMPLETED|FAILED`; el cliente consulta el estado y el avance hasta terminar.

## Domain rules / invariants
- **INV-04, INV-05, INV-06, INV-07, INV-08, INV-10 (existentes):** sin cambios (carga por venta, idempotente, mismas reglas).
- **INV-09 (modificada):** una sola corrida **activa** (`QUEUED` o `RUNNING`) por empresa.
- **INV-11 (nueva):** el worker toma empresa, usuario y nombre de la corrida guardada, nunca de una petición; toda consulta filtra por `company_id`.
- **INV-12 (nueva):** transiciones permitidas: `PREVIEWED|FAILED|UPLOADED(con firma) → QUEUED → RUNNING → COMPLETED|FAILED`; `COMPLETED` no se re-encola; `RUNNING` sin latido > 15 min pasa a `FAILED` (`interrupted`).

## Acceptance criteria
- **AC-01** `POST …/execute/` con previsualización vigente responde 202 con `status: QUEUED` sin cargar ninguna venta en la petición; las validaciones actuales (mapeo, opciones, firma, capacidades, almacén) siguen respondiendo 400/409 igual.
- **AC-02** El worker toma una corrida `QUEUED`, la pasa a `RUNNING`, carga las ventas con las mismas reglas y la deja `COMPLETED` con los mismos contadores y resultados por venta que antes.
- **AC-03** Mientras corre, `GET …/<id>/` expone `status`, `processed`, `total` y `counts`; `processed` crece por venta.
- **AC-04** Con otra corrida `QUEUED/RUNNING` en la empresa, `execute` de otra responde 409 `import_running`; reenviar `execute` de la **misma** corrida con la misma `idempotency_key` devuelve su estado actual sin duplicar.
- **AC-05** Si la revalidación del worker falla (módulo deshabilitado, firma distinta, error inesperado de infraestructura) la corrida termina `FAILED` con `failure_code` y `failure_message`; nunca queda `RUNNING` ni sin dueño.
- **AC-06** Una corrida `RUNNING` sin latido > 15 min pasa a `FAILED` (`interrupted`) al iniciar el worker y periódicamente; reintentarla no duplica ventas (`SKIPPED_DUPLICATE`).
- **AC-07** Dos workers simultáneos no toman la misma corrida (`skip_locked`).
- **AC-08** Aislamiento: estado/filas de una corrida de otra empresa → 404; el worker ejecuta con la empresa y usuario de la corrida.
- **AC-09** UI paso 4: tras confirmar, muestra «En cola» y luego barra «Procesando n de N» (DDR), sondea cada 3 s y termina mostrando el resultado actual; `?run=` retoma corridas en cola/en curso; fallo del proceso en `alert-danger` con «Volver a intentar».
- **AC-10** Historial y detalle muestran `QUEUED`/`RUNNING` con badge de texto, y el mensaje de fallo si lo hay; todo por `translate` con las mismas claves en es/en/pt.
- **AC-11** `compose.yaml` define `import-worker` con la misma imagen, entorno y red `database`, sin puertos; `docker compose config` valida y el despliegue lo levanta con el `up -d --wait` existente.

## Edge cases / Error cases
- Worker apagado: la corrida permanece `QUEUED`; la UI lo comunica como «En cola»; `run_import_worker --once` la procesa a mano.
- Reinicio del worker a mitad de corrida: `FAILED interrupted` tras 15 min; reintento idempotente.
- Doble clic / reintento de red en «Cargar»: misma `idempotency_key`, sin segunda corrida (AC-04).
- Excepción no controlada dentro del worker: se registra, la corrida queda `FAILED` y el bucle sigue con la siguiente.
- Archivo ya `COMPLETED`: `execute` devuelve su resultado guardado (200) como hoy.

## Authorization / permissions
Sin cambios: solo administradores con `sales` y `catalog` habilitados (`required_modules`); el worker no autentica personas, solo ejecuta corridas ya autorizadas al encolar.

## API contract
- **API-01 (cambia, compatible solo con el frontend nuevo):** `POST /api/imports/sales/<id>/execute/` → 202 `{id, status, counts, processed, total, rows_url}` (200 si ya `COMPLETED`). Backend y frontend salen juntos.
- **API-02 (extiende):** `GET /api/imports/sales/<id>/` añade `processed`, `total`, `failure: {code, message} | null`; el listado añade `status` ya existente y `processed/total`. Campos nuevos son aditivos.

## UI behavior
- **UI-01** Paso 4 «en cola» y «en curso» según el DDR (plantilla del asistente, `.progress`, `role=status`, alerta tenue, enlace al historial).
- **UI-02** Retomar `?run=` para `QUEUED|RUNNING` (sondeo) además de `COMPLETED|FAILED`.
- **UI-03** Badge `info` con texto para `QUEUED`/`RUNNING` en historial y detalle.

## Non-functional requirements
La petición `execute` responde en < 1 s independientemente del tamaño; el sondeo (`GET`) no carga `rows` (`defer`); sin dependencias nuevas.

## Out of scope
Celery/Redis, reencolado automático de corridas caídas, cancelar una corrida, notificaciones, paralelismo entre empresas, optimizar las consultas por venta, cambiar el timeout de Gunicorn/Nginx.

## Open questions
Ninguna que bloquee.

# Test Specification

## Unit tests
Caso de uso de encolado (validaciones, firma obsoleta, idempotencia por clave, `import_running` con `QUEUED`); caso de uso de ejecución con fakes: progreso, `FAILED` con `failure_*` ante revalidación fallida (AC-01..AC-05).

## Integration tests
BD de prueba: API `execute` 202 + estado; `run_import_worker --once` ejecuta una corrida de extremo a extremo y coincide con el resultado síncrono previo (reutiliza los fixtures de `tests/test_api_integration.py`); `skip_locked` con dos reclamos; recuperación de `RUNNING` caída; aislamiento por empresa en worker y API (AC-02..AC-08); migración (restricción nueva).
Frontend (Karma): servicio (202, `processed/total`), componente (en cola → progreso → resultado, retomar, fallo, sondeo se detiene al destruir), historial/detalle (badges) (AC-09, AC-10); `npm run i18n:check` y la prueba de claves iguales.
Despliegue: pruebas de `backend/config/test_production_deployment.py` ampliadas para `import-worker` (AC-11).

## E2E (¿corresponde?)
**NO** — la cadena API + worker + sondeo se cubre con integración de backend y pruebas de componente; no se instala Playwright.

## Regression tests
Se conservan las pruebas actuales de carga por venta, idempotencia (INV-05), rollback por venta (INV-04) y frontera de módulos (AC-20 del plan previo), ahora ejecutadas a través del worker.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | Unit encolado + integración API (202, 400/409 previos) |
| AC-02 | Integración `run_import_worker --once` vs. resultado esperado |
| AC-03 | Integración API GET durante la corrida (progreso por venta, con fake de reloj/hook) + unit |
| AC-04 | Unit + integración (otra corrida activa; misma clave) |
| AC-05 | Unit fakes + integración (módulo deshabilitado tras encolar) |
| AC-06 | Integración con `heartbeat_at` antiguo |
| AC-07 | Integración de dos reclamos consecutivos / concurrentes (`Barrier`, patrón existente en el repo) |
| AC-08 | Integración con dos empresas |
| AC-09 | Karma componente + servicio |
| AC-10 | Karma historial/detalle + `i18n:check` + prueba de claves |
| AC-11 | `test_production_deployment.py` + `docker compose config` |

# Implementation Plan

## Architecture considerations
Seguir `docs/architecture/ddd.md`: reglas en `application/`, puertos en `ports.py`, Django solo en `infrastructure/`. El comando del worker es composición, sin reglas de negocio.

## Proposed solution
Ver ADR. Partir `ExecuteSalesImport` en `EnqueueSalesImport` (validar + `QUEUED`) y la carga existente que el worker invoca con la corrida ya reclamada (la validación se repite por seguridad); añadir en el repositorio `enqueue`, `claim_next` (`skip_locked`), `fail_stale`, `set_progress`/`fail`.

## Files/components affected
- **Backend:** `modules/data_import/application/{use_cases,ports}.py`, `domain/errors.py` (si hace falta), `infrastructure/django/{models,repositories}.py`, nuevo `infrastructure/worker.py` y `management/commands/run_import_worker.py`, `api/views.py`, `api/urls.py` (sin cambios de ruta), tests en `modules/data_import/tests/`.
- **Migraciones:** `data_import/migrations/0003_…` (campos `processed_count`, `failure_code`, `failure_message`, estado `QUEUED`, restricción `di_run_one_active_per_company` sobre `QUEUED|RUNNING` reemplazando `di_run_one_running_per_company`).
- **Frontend:** `features/data-import/{models,services,pages/sales-import,pages/import-history,pages/import-detail}`, `assets/i18n/{es,en,pt}.json`, specs.
- **Infra/docs:** `compose.yaml`, `backend/config/test_production_deployment.py`, `docs/deployment/docker.md`, nota en el ADR previo.

## Implementation steps
1. Migración 0003 + modelo (estado `QUEUED`, campos nuevos, restricción) — INV-09, INV-12.
2. Puertos y repositorio: `enqueue`, `claim_next`, `fail_stale`, progreso y `fail` — AC-04..AC-07.
3. Casos de uso: `EnqueueSalesImport`; adaptar `ExecuteSalesImport` para correr sobre una corrida ya reclamada con progreso y `FAILED` controlado — AC-01..AC-05.
4. Worker (`run_import_worker`, `--once`, sondeo, limpieza de caídas, captura de excepciones) — AC-02, AC-05..AC-08.
5. API: `execute` → 202; `GET` con `processed/total/failure`; listado con progreso — API-01/02.
6. Frontend: servicio y modelos, paso 4 con sondeo y retomar, historial/detalle, i18n es/en/pt — AC-09, AC-10.
7. `compose.yaml` + pruebas de despliegue + `docs/deployment/docker.md` (operación manual y logs) + nota de reemplazo parcial en el ADR previo — AC-11.
8. Pruebas, `ruff`/`flake8` sobre `.py` cambiados, `npm run lint`/`test`/`i18n:check`.

## Database / migrations
Una migración nueva, reversible. No se edita 0001/0002. Valores por defecto en los campos nuevos; sin migración de datos.

## Risks
Servicio nuevo sin levantar → corridas en cola (mitigado en ADR y documentación); despliegue a mitad de corrida (reintento idempotente); cambio de contrato (salen juntos).

## New dependencies
Ninguna.
