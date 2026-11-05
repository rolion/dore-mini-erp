# ADR-github-actions-deploy-produccion-pipeline-y-secretos: Pipeline de deploy a producción con GitHub Actions

**Estado:** Propuesto
**Task relacionado:** TASK-github-actions-deploy-produccion
**Fecha:** 2026-11-05

## Contexto
El deploy hoy es manual en el droplet (`docs/deployment/docker.md`). Se pide que cada merge a `main` construya las imágenes y corra las migraciones, con las credenciales de BD inyectadas desde GitHub. El droplet es pequeño (1 GiB): construir Angular allí es frágil. El stack ya existe (`compose.yaml`), con PostgreSQL y proxy externos.

## Decisión
Un workflow `.github/workflows/deploy.yml` con trigger `push` a `main` (cubre el merge de un PR) y `workflow_dispatch` (re-ejecución manual), en el *environment* `production` de GitHub y con `concurrency` serializada (`cancel-in-progress: false`).

Pasos:
1. **Checkout** del commit de `main`; `IMAGE_TAG` = SHA corto (tag inmutable).
2. **Build en el runner** de GitHub (`docker build` de `backend/` y `frontend/panel_admin/` con los tags `pocketbiz-backend:<tag>` y `pocketbiz-frontend:<tag>`, los mismos nombres que usa `compose.yaml`).
3. **Transferencia por SSH** sin registry: `docker save | gzip | ssh … docker load`, más copia de `compose.yaml` y del script remoto al directorio de deploy. Evita credenciales de registry en el droplet y deja `compose.yaml` sin cambios.
4. **En el droplet** (`scripts/deploy/remote-deploy.sh`): backup `pg_dump` de la BD de la app (aborta si falla; conserva los últimos N), `docker compose run --rm --no-deps backend python manage.py migrate --noinput`, `docker compose up -d --no-build --wait`, y poda de imágenes antiguas conservando las últimas releases para rollback.
5. **Smoke check** desde el runner contra `https://www.pocketbiz.website/api/health/`.

**Secretos y variables** (GitHub *environment* `production`):
- Secrets: `DEPLOY_SSH_KEY`, `DEPLOY_KNOWN_HOSTS`, `SECRET_KEY`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`.
- Variables: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_PATH`, `DATABASE_NETWORK`; opcionales `DB_HOST` (def. `db_v2`), `DB_PORT` (def. `5432`), `DB_CONTAINER` (def. `db_v2`), `TIME_ZONE`, `REGISTRATION_ENABLED`.

`DATABASE_URL` se arma en el script remoto desde `DB_USER/DB_PASSWORD/DB_NAME` con la contraseña codificada como URL. Los valores viajan por stdin del SSH y solo existen como variables de entorno del proceso de deploy (no se escriben a disco ni a imágenes). La host key se verifica con `DEPLOY_KNOWN_HOSTS` (no `ssh-keyscan`). `permissions: contents: read`.

## Alternativas consideradas
- *Runner self-hosted en el droplet*: build en 1 GiB y un agente con acceso al docker del host siempre expuesto; descartado.
- *GHCR + pull en el droplet*: estándar, pero exige token de lectura guardado en el host y renombrar imágenes en `compose.yaml`; más piezas sin necesidad real hoy.
- *SSH + `git pull` y build en el droplet*: reproduce el problema de memoria.
- *Migraciones automáticas en el entrypoint*: contradice el ADR de Docker vigente; se mantienen como paso explícito del pipeline.
- *Gate de tests en el workflow*: valioso pero fuera de alcance (no existe CI de tests aún); se recomienda como task aparte.

## Estrategia de rollback / mitigación
Tags inmutables por SHA y últimas N imágenes retenidas: re-ejecutar el workflow (`workflow_dispatch`) sobre un commit anterior, o en el droplet `IMAGE_TAG=<previo> docker compose up -d --no-build --wait`. El rollback de imagen no deshace migraciones: el backup `pg_dump` previo (`$DEPLOY_PATH/backups/`) permite restaurar; migraciones destructivas requieren su propio plan de compatibilidad. Si migrar falla, el script aborta antes de `up`, dejando corriendo la versión anterior. Si el healthcheck de `up --wait` falla, el job queda rojo. Nunca `down -v`.

## Consecuencias
Deploy reproducible y sin intervención por merge. Requiere que la persona administradora configure una vez secrets/variables, la llave SSH de deploy y el environment `production` (guía en `docs/deployment/github-actions.md`). Cada merge a `main` despliega: se recomienda proteger `main` y, si se quiere un freno manual, requerir aprobación en el environment. Sin gate de tests, un merge roto llega a producción.
