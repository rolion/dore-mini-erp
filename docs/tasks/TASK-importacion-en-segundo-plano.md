# TASK-importacion-en-segundo-plano: Ejecutar la importación de ventas en segundo plano para que no la aborte el timeout

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-importacion-en-segundo-plano
**Pull Request:** _sin abrir todavía_

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-20 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-11-20 | INVESTIGATION → ARCHITECTURE | NEEDS_ARCHITECTURE: cambia el modelo de ejecución, el contrato API y la infraestructura | delivery-start |
| 2026-11-20 | ARCHITECTURE → DESIGN → PLANNING → ENGINEERING | ADR + DDR + PLAN v1 listos, Specification READY | delivery-start |

## Investigación

### Requerimiento
La persona importa un archivo de ventas y la ejecución tarda más de 30 s: Gunicorn aborta el worker y la petición responde 500 sin cuerpo. Pide **importar en lotes o en segundo plano**, aceptando que es un cambio de diseño del módulo de importación. Aporta el log de producción (`pocketbiz-backend-1`).

### Hechos encontrados
- Log de producción: `POST /api/imports/sales/<id>/execute/` → 500 y `gunicorn/workers/base.py:199 handle_abort → sys.exit(1)` (`SystemExit`) mientras la corrida estaba en una consulta de `CompanyModuleModel`; después `Worker exiting`. Es el `--timeout` por defecto de Gunicorn (30 s), no un error de negocio.
- `backend/Dockerfile:20` — `gunicorn … --workers 2` (workers `sync`, sin `--timeout`, sin hilos). Con 2 workers, una importación larga ocupa la mitad de la capacidad de la API.
- `backend/modules/data_import/api/views.py:125-140` — `RunExecuteView.post` ejecuta `ExecuteSalesImport.execute` **dentro de la petición** y responde 200 con `counts` y `rows_url`.
- `backend/modules/data_import/application/use_cases.py:369-414` — `ExecuteSalesImport.execute`: valida mapeo/opciones/firma, `claim`, recorre día a día (`_prepare_day` compra por proveedor, luego `_load_sale` por venta, cada una en su `atomic()`), con `heartbeat` por venta y `finish(COMPLETED|FAILED)`. Hasta 2 000 filas (`docs/adr/ADR-cargar-ventas-desde-archivo-ejecucion-por-venta-e-idempotencia.md`, punto 8).
- Cada venta toca varios módulos (`use_cases.py:470-507`, `infrastructure/adapters.py:151`): decenas de consultas por venta; el 30 s se agota con pocas centenas de ventas.
- `backend/modules/data_import/infrastructure/django/models.py:7-46` — `ImportRun` ya tiene `RUNNING`, `started_at`, `heartbeat_at`, `idempotency_key` y la restricción `di_run_one_running_per_company` (INV-09).
- `backend/modules/data_import/infrastructure/django/repositories.py:12,50-67` — `claim` marca `FAILED` una corrida `RUNNING` sin latido en 15 min (`STALE_AFTER`) y borra sus resultados al reintentar; `existing_keys` + `ImportedSale` (clave única `company_id, source_key`) hacen la carga idempotente por venta (INV-05): reintentar tras una caída no duplica.
- `ImportRunModel` guarda `company_id`, `created_by_id`, `created_by_name`, `headers`, `rows`, `mapping`, `options`: la corrida tiene todo lo que un proceso aparte necesita para ejecutarla sin petición HTTP.
- `SalesImportAdapter(company_id, user_id, user_name)` (`adapters.py:35-52`) no depende de `request`; `views.py:45-46` solo lo construye desde él.
- `frontend/panel_admin/src/app/features/data-import/services/sales-import-api.service.ts:248-258` — `execute()` espera `{id, status, counts}`; `pages/sales-import/sales-import.component.ts:371-393` pasa al paso 4 con ese resultado; `:128-148` solo retoma corridas `COMPLETED|FAILED` (otras muestran `RESUME_UNAVAILABLE`). `import-history.component.ts:15-25` ya conoce `RUNNING`.
- No existe cola de trabajos, Celery, Redis ni segundo proceso: `compose.yaml` solo tiene `backend` y `frontend`; `scripts/deploy/remote-deploy.sh:73-76` hace `migrate` y `docker compose up -d --no-build --wait`. El ADR previo difirió Celery explícitamente («se difiere; el límite de filas acota el riesgo»).
- `docker-entrypoint.sh` ejecuta `collectstatic` y luego `exec "$@"`: un servicio con otro `command` reutiliza la misma imagen.

### Hipótesis / supuestos no confirmados
- Subir `--timeout` de Gunicorn (y los timeouts del proxy/Nginx) taparía el síntoma con archivos de ~2 000 filas, pero ata un worker de la API durante minutos y no escala; la persona pidió explícitamente lotes/segundo plano.
- Tiempo por venta en producción: no medido. El diseño no depende de él.

### Módulos y dependencias relacionadas
`data_import` (api/application/infrastructure/migrations), frontend `features/data-import`, `compose.yaml`, `scripts/deploy/remote-deploy.sh`, `backend/config/test_production_deployment.py` y `test_deploy_pipeline.py`, `docs/deployment/`.

### Implementaciones similares existentes
Ninguna asíncrona. Se reutiliza el patrón de latido + corrida caída de `claim`/`heartbeat`.

### Comportamiento actual
Ejecutar = petición bloqueante; si pasa de ~30 s el worker muere, la corrida queda `RUNNING` hasta 15 min sin latido (409 «en curso» al reintentar) y la persona ve un error genérico.

### Restricciones
`CLAUDE.md`: aislamiento por `company_id`, sin dependencias nuevas sin avisar, migraciones nuevas (nunca editar), tests de frontera de módulos, textos por `translate` en es/en/pt, una rama y un PR.

### Riesgos identificados
- Un servicio nuevo en producción: si el worker no está levantado, las corridas quedan en cola.
- Un despliegue (reinicio) a mitad de una corrida la interrumpe.
- Cambio de contrato de `execute` (200 → 202): backend y frontend deben salir juntos.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — cambia el modelo de ejecución (síncrono → cola), el contrato API, la máquina de estados de `ImportRun` y la infraestructura (nuevo servicio en `compose.yaml` y en el despliegue).

### Diseño requerido
**SI** — el paso 4 del asistente pasa de «resultado inmediato» a «en cola / en curso con progreso / resultado», con retomar y estados nuevos en el historial.

## Diseño
Ver `docs/design/DDR-importacion-en-segundo-plano-progreso-de-la-importacion.md`.

## Arquitectura
Ver `docs/adr/ADR-importacion-en-segundo-plano-cola-en-base-de-datos-y-worker.md`.

## Plan
`docs/plans/PLAN-2026-11-20-importacion-en-segundo-plano.md` (v1, COMPLETO). Specification readiness: READY.

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
