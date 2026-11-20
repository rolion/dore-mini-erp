# TASK-importacion-en-segundo-plano: Ejecutar la importación de ventas en segundo plano para que no la aborte el timeout

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-importacion-en-segundo-plano
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/113

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-20 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-11-20 | INVESTIGATION → ARCHITECTURE | NEEDS_ARCHITECTURE: cambia el modelo de ejecución, el contrato API y la infraestructura | delivery-start |
| 2026-11-20 | ARCHITECTURE → DESIGN → PLANNING → ENGINEERING | ADR + DDR + PLAN v1 listos, Specification READY | delivery-start |
| 2026-11-20 | ENGINEERING → REVIEW | Implementación completa según PLAN v1 | delivery-build |
| 2026-11-20 | REVIEW → PUBLISH | Quality Gate PASS (5 hallazgos Low/Medium abiertos) | delivery-publish |

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
**Resumen.** `execute` ahora valida y encola (202); el worker `run_import_worker` (servicio `import-worker` en `compose.yaml`) ejecuta la carga por venta con la empresa y el usuario guardados en la corrida; la interfaz sondea el avance cada 3 s y permite retomar con `?run=`.

**Cobertura del plan**
- INV-09/INV-12, AC-04..AC-07: migración `0003_import_queue` (estado `QUEUED`, `processed_count`, `total_count`, `failure_*`, restricción `di_run_one_active_per_company`), `DjangoImportRepository.enqueue/fail/heartbeat(progreso)/get_status` y `DjangoImportQueue.claim_next` (`select_for_update(skip_locked)`) / `fail_stale`.
- AC-01..AC-05: `EnqueueSalesImport` y `ExecuteSalesImport.run_claimed` (`application/use_cases.py`); revalidación y excepciones terminan en `FAILED` con código y mensaje.
- AC-02, AC-06, AC-08: `infrastructure/worker.py` y `management/commands/run_import_worker.py` (`--once`, `--poll`, cierre ordenado con SIGTERM).
- API-01/02: `RunExecuteView` (202/200), `RunDetailView` con `processed/total/failure` sin cargar el archivo.
- AC-09, AC-10 (UI-01..03): paso 4 con en cola / progreso / fallo, sondeo y retomar; `QUEUED` en historial y detalle; claves i18n es/en/pt.
- AC-11: `compose.yaml` (`import-worker`), `ImportWorkerServiceTests`, `docs/deployment/docker.md`.

**Pantalla de referencia / componentes:** asistente existente (`sales-import`) y plantilla «previsualización obligatoria»; reutiliza `app-status-badge`, `app-import-counts`, `app-import-rows`, alerta tenue `bg-info-subtle`. Sin componentes compartidos nuevos ni cambios en `design-system.md` (según DDR).

**Desviaciones respecto al plan**
- `ExecuteSalesImport.execute` (carga síncrona) se conserva para pruebas y como camino reutilizable; ya no lo usa la API. Deuda menor: unificar cuando se retire.
- La prueba de «dos reclamos simultáneos» (AC-07) es secuencial (el segundo reclamo no encuentra nada); la exclusión real recae en `skip_locked` de PostgreSQL y no se probó con hilos.
- `stop_grace_period: 2m` y `depends_on: backend` añadidos al servicio (no estaban en el ADR; operativos).

**Verificación propia (no es el Quality Gate):** frontend `ng test` completo 1745/1745, `ng lint` y `i18n:check` limpios; backend: pruebas de casos de uso/dominio y la de compose corridas con configuración mínima de Django; `flake8` limpio en lo cambiado; `docker compose config` válido. **No se corrieron** las pruebas de integración de backend ni la migración: el entorno local no tiene PostgreSQL, `psycopg` ni Django 5.2 (migración escrita a mano, sin `makemigrations`).

**Deuda / notas:** consultas por venta sin optimizar (fuera de alcance); sin reencolado automático de corridas caídas ni cancelación.

## Review
**Quality Gate: PASS** (subagente aislado, 2026-11-20). Sin hallazgos Critical/High; 0 pruebas fallando.
Hallazgos (Medium/Low, no bloquean; registrados como REV; REV-01..03 resueltos después, REV-04..05 abiertos):
- [REV-2026-11-20-importacion-en-segundo-plano-01](docs/reviews/REV-2026-11-20-importacion-en-segundo-plano-01.md) — Low, IMPLEMENTATION: Doble envio concurrente con la misma clave responde 409
- [REV-2026-11-20-importacion-en-segundo-plano-02](docs/reviews/REV-2026-11-20-importacion-en-segundo-plano-02.md) — Low, IMPLEMENTATION: finish() y fail() actualizan sin condicion de estado
- [REV-2026-11-20-importacion-en-segundo-plano-03](docs/reviews/REV-2026-11-20-importacion-en-segundo-plano-03.md) — Medium, SPECIFICATION: Pruebas mas debiles que la tabla AC -> verificacion del plan
- [REV-2026-11-20-importacion-en-segundo-plano-04](docs/reviews/REV-2026-11-20-importacion-en-segundo-plano-04.md) — Low, DESIGN: Altura inline en la barra de progreso
- [REV-2026-11-20-importacion-en-segundo-plano-05](docs/reviews/REV-2026-11-20-importacion-en-segundo-plano-05.md) — Low, ARCHITECTURE: El servicio import-worker no tiene healthcheck
Revisión visual: **no verificada** (la app no se levantó en navegador); sí revisada por lectura contra la sección 8 del sistema de diseño (sin HEX/fuentes propias, textos por `translate` en es/en/pt, roles ARIA, estados cubiertos).


## Publicación
PR #113 listo para aprobación humana (nunca mergeado por el flujo). Cambio sensible: **base de datos (migración 0003) e infraestructura (nuevo servicio `import-worker`)**, respaldado por el ADR de cola en base de datos. REV-01, REV-02 y REV-03 corregidos y resueltos tras el Quality Gate (pruebas de `modules.data_import` + `config`: 81 OK con PostgreSQL 16, flake8/ruff limpios); REV-04 (altura inline) y REV-05 (healthcheck del worker) siguen abiertos como Low.
