# ADR-importacion-en-segundo-plano-cola-en-base-de-datos-y-worker: La importación se encola en la base y la ejecuta un worker propio

**Estado:** Propuesto
**Task relacionado:** TASK-importacion-en-segundo-plano
**Fecha:** 2026-11-20

## Contexto
`POST /api/imports/sales/<id>/execute/` carga todas las ventas dentro de la petición. Gunicorn (sync, 2 workers, timeout 30 s) aborta el worker cuando la carga tarda más, la respuesta es un 500 sin cuerpo y la corrida queda colgada. El ADR `ADR-cargar-ventas-desde-archivo-ejecucion-por-venta-e-idempotencia` (punto 8, «Ejecución síncrona dentro de la petición», y la alternativa «Cola de trabajos asíncrona (Celery)») dejó este cambio para cuando hiciera falta: hace falta. La carga ya es por venta, idempotente (`ImportedSale`), con latido y recuperación de corridas caídas, así que lo único que falta es **quién** la ejecuta y **cómo** se entera la persona.

## Decisión
1. **Cola en la propia base (`ImportRun`)**, sin dependencias nuevas. `execute` valida igual que hoy (mapeo, opciones, firma de la vista previa, capacidades, almacén) y, en vez de cargar, pasa la corrida a `QUEUED` y responde **202** `{id, status: 'QUEUED', counts, progress}`.
2. **Estados**: `UPLOADED → PREVIEWED → QUEUED → RUNNING → COMPLETED | FAILED`. La restricción de INV-09 pasa a cubrir `QUEUED` **y** `RUNNING` (una sola corrida activa por empresa; migración nueva que reemplaza la restricción). Reenviar `execute` con la misma `idempotency_key` sobre una corrida `QUEUED/RUNNING/COMPLETED` devuelve su estado actual (200/202), no 409; con otra corrida activa en la empresa sigue siendo 409 `import_running`.
3. **Worker**: comando `python manage.py run_import_worker` (bucle de sondeo cada ~2 s; `--once` para pruebas y operación manual). Reclama una corrida `QUEUED` con `select_for_update(skip_locked=True)`, la pasa a `RUNNING` y ejecuta el **mismo** caso de uso de carga por venta, construyendo el `SalesImportAdapter` con `company_id`, `created_by_id` y `created_by_name` guardados en la corrida (nunca de una petición). Cada corrida usa su propio repositorio con `company_id` (aislamiento intacto).
4. **Servicio nuevo `import-worker` en `compose.yaml`**: misma imagen que `backend` (`image: pocketbiz-backend`), `command: python manage.py run_import_worker`, mismas variables de entorno y red `database`, `restart: unless-stopped`; sin puerto ni volumen de estáticos. `remote-deploy.sh` ya hace `docker compose up -d --no-build --wait`, que lo levanta; no se toca `deploy.yml`.
5. **Progreso y fallo visibles**: campos nuevos en `ImportRun` (`processed_count`, `failure_code`, `failure_message`). El worker actualiza `processed_count` junto al latido (por venta). Si la revalidación del worker falla (p. ej. un módulo se deshabilitó entre el encolado y la ejecución) la corrida termina `FAILED` con código y mensaje en vez de lanzar una excepción sin dueño. `GET /api/imports/sales/<id>/` y el listado exponen `status`, `counts`, `processed`, `total` (= filas de ventas a cargar) y `failure`.
6. **Corrida caída** (reinicio del worker o del servidor): el worker, al iniciar y cada minuto, marca `FAILED` las `RUNNING` sin latido en 15 min (`STALE_AFTER`, hoy hecho solo dentro de `claim`) con `failure_code='interrupted'`. Reintentar es seguro por idempotencia: lo ya cargado sale como «Ya importada». No se reencola solo.
7. **Frontera**: la lógica sigue en `data_import` (use cases + puertos); el worker es un comando de `management/commands/` en la capa de infraestructura que solo compone repositorio, adaptador y caso de uso. Ningún otro módulo importa `data_import`.
8. **Gunicorn no cambia**: la API responde en milisegundos; no se sube el timeout.

## Alternativas consideradas
- **Subir `--timeout` de Gunicorn y de Nginx:** una línea, pero ata un worker de 2 durante minutos, hay un techo (proxy, navegador) y vuelve a fallar con archivos mayores. Descartada como solución; no se aplica ni como parche.
- **Hilo dentro del worker de Gunicorn (`threading.Thread` tras responder):** sin infraestructura nueva, pero muere con el reciclado/reinicio del worker, compite por CPU con la API y no tiene dueño si el proceso cae. Descartada.
- **Lotes dirigidos por el navegador** (cada petición carga N ventas y el cliente repite): sin infraestructura, pero exige que la pestaña siga abierta y partir un día a la mitad complica las compras por proveedor/día. Descartada.
- **Celery + Redis/RabbitMQ:** estándar y escalable, pero añade dos dependencias y un servicio externo para un volumen de ≤ 2 000 filas por archivo. Se mantiene diferida; la cola en base se reemplaza sin tocar el caso de uso si algún día se necesita.

## Estrategia de rollback / mitigación
- Migración nueva y reversible (campos con valor por defecto + restricción reemplazada); no toca tablas de otros módulos. Las corridas históricas siguen válidas.
- Despliegue: backend y frontend salen juntos en el mismo PR (el contrato de `execute` cambia a 202). Si hay que revertir, se revierte el commit y se redespliega; el servicio `import-worker` sobrante se elimina con `docker compose up -d --remove-orphans`.
- Si el worker no está levantado, la corrida queda `QUEUED`: la UI lo dice («en cola») y el historial la muestra; `docker compose logs import-worker` y `docker compose exec backend python manage.py run_import_worker --once` documentados en `docs/deployment/` permiten procesarla a mano. Una corrida `QUEUED` no vence sola.
- Antes del primer despliegue no hay corridas `QUEUED`; no hay migración de datos.

## Consecuencias
- Un proceso más en producción (memoria de un segundo proceso Django) y un comando que operar.
- La persona deja de esperar bloqueada: ve progreso y puede salir y volver (`?run=` retoma).
- Cambio de contrato de `execute` (200 con resultado → 202 con estado); pruebas y cliente se actualizan.
- Una corrida interrumpida por un despliegue exige reintento manual (idempotente).
- Sigue habiendo un solo worker secuencial: dos empresas no se ejecutan en paralelo; aceptable al volumen actual y escalable levantando más réplicas (el `skip_locked` ya lo permite).
