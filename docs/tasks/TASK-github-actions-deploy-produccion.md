# TASK-github-actions-deploy-produccion: Deploy automático a producción con GitHub Actions

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** NO
**Rama:** task/TASK-github-actions-deploy-produccion
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/64

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-05 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-11-05 | INVESTIGATION → ARCHITECTURE | Infraestructura + migraciones de BD + secretos | delivery-start |
| 2026-11-05 | ARCHITECTURE → PLANNING → ENGINEERING | ADR y PLAN v1 escritos, spec READY | delivery-start |
| 2026-11-05 | ENGINEERING → REVIEW | Implementación completa | delivery-build |
| 2026-11-05 | REVIEW → ENGINEERING → REVIEW | Ciclo 1 FAIL, correcciones REV-01..04 | delivery-publish |
| 2026-11-05 | REVIEW → PUBLISH | Ciclo 2 PASS | delivery-publish |

## Investigación

### Requerimiento
«Establecer un proceso de deploy mediante GitHub Actions: cada vez que se hace merge de un branch a `main` debe ejecutarse un action que baje la última versión de `main`, construya las imágenes de Docker y corra las migraciones. Hay variables que deben setearse antes, como las cuentas de usuario de la DB; se pueden setear mediante GitHub Actions.»

### Hechos encontrados
- `compose.yaml:1-92` — stack `pocketbiz` con `backend` y `frontend`; imágenes `pocketbiz-backend:${IMAGE_TAG:-latest}` y `pocketbiz-frontend:${IMAGE_TAG:-latest}`; exige `SECRET_KEY`, `DATABASE_URL` y `DATABASE_NETWORK` (`:?`), que son las variables a inyectar.
- `compose.yaml` (redes) — red externa `proxy` (nginx-proxy + acme ya existentes en el droplet) y red de BD externa `${DATABASE_NETWORK}`; el PostgreSQL (`db_v2`) ya corre en el host y no lo gestiona este stack.
- `backend/docker-entrypoint.sh:4-5` — las migraciones NO corren al arrancar a propósito: son un comando explícito de despliegue.
- `docs/deployment/docker.md` — procedimiento manual vigente: build, backup de PostgreSQL, `docker compose run --rm --no-deps backend python manage.py migrate --noinput`, `up -d --wait`, smoke checks, rollback por `IMAGE_TAG`. Advierte que el build de Angular en un droplet de 1 GiB puede fallar por memoria y recomienda un builder/CI que transfiera las imágenes.
- `docs/adr/ADR-docker-production-deployment-proxy-and-database.md` — ADR vigente: tags de imagen inmutables, backup antes de migrar, migraciones explícitas, secretos solo en runtime, nunca `down -v`.
- `backend/config/settings/production.py:6-8` — `SECRET_KEY` y `DATABASE_URL` se leen del entorno.
- `git remote -v` — `git@github.com:rolion/dore-mini-erp.git`. No existe `.github/` (no hay workflows).
- `frontend/panel_admin/Dockerfile:1-17` — build multi-stage Node 22; `backend/Dockerfile` Python 3.12/Gunicorn.

### Hipótesis / supuestos no confirmados
- El droplet es accesible por SSH desde GitHub (puerto 22 abierto) con una llave dedicada de deploy.
- El usuario de deploy en el droplet puede ejecutar `docker` (grupo `docker`).
- El contenedor de BD se llama `db_v2` (según `docs/deployment/docker.md`) y la cuenta de aplicación puede hacer `pg_dump` de su propia base.

### Módulos y dependencias relacionadas
Solo infraestructura: `compose.yaml`, Dockerfiles, `docs/deployment/`. Ningún módulo de negocio.

### Implementaciones similares existentes
Ninguna en CI; el flujo manual de `docs/deployment/docker.md` es la referencia a automatizar.

### Comportamiento actual
El deploy es 100 % manual en el droplet.

### Restricciones
`CLAUDE.md`: no commitear secretos ni tocar `.env`; avisar antes de instalar dependencias (el plan no añade ninguna, solo actions oficiales de GitHub); las migraciones no se editan. El ADR de Docker vigente no se contradice, se automatiza.

### Riesgos identificados
- Migrar sin backup (mitigado: backup obligatorio que aborta el deploy si falla).
- Dos deploys simultáneos (mitigado: `concurrency`).
- Build de Angular sin memoria en el droplet (mitigado: build en el runner de GitHub).
- Fuga de secretos en logs (mitigado: GitHub Secrets enmascarados; nada en imágenes).
- Migración incompatible con la versión anterior: el rollback de imagen no deshace esquema (se documenta).

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — infraestructura de despliegue, manejo de secretos y migraciones sobre la BD de producción.

### Diseño requerido
**NO** — sin pantallas ni cambios visuales.

## Diseño
No aplica.

## Arquitectura
`docs/adr/ADR-github-actions-deploy-produccion-pipeline-y-secretos.md`

## Plan
`docs/plans/PLAN-2026-11-05-github-actions-deploy-produccion.md` (v1, COMPLETO, READY)

## Implementación
Workflow `.github/workflows/deploy.yml` (AC-01, AC-02, AC-05, INV-04), script remoto `scripts/deploy/remote-deploy.sh` (AC-03, AC-04, INV-01..03), guía `docs/deployment/github-actions.md` (AC-06) y enlaces en `docker.md` y `CLAUDE.md`. Pruebas estáticas en `backend/config/test_deploy_pipeline.py` (7 pruebas, pasan localmente).

Desviaciones: el script remoto se envía por stdin (no se copia al droplet); el tag es el SHA de 12 caracteres. Deuda: el flujo real contra el droplet no se pudo probar (requiere secrets y servidor); queda para el primer merge. Sin gate de tests (fuera de alcance).

## Review
Ciclo 1: FAIL (REV-01 y REV-02 High, REV-03 y REV-04 Medium, todos IMPLEMENTATION), corregidos en el commit siguiente. Ciclo 2: PASS (subagente aislado). `python -m unittest config.test_deploy_pipeline config.test_production_deployment`: 16 pruebas OK; `bash -n` OK. No ejecutado: shellcheck (no instalado) ni un deploy real contra el droplet. Low abiertos: la prueba con docker falso no detecta por sí sola la vuelta a `bash -s` (lo cubre una aserción de texto sobre deploy.yml); los secrets están en el `env` de todo el job.

## Publicación
PR #64 listo para aprobación humana. Cambio sensible: infraestructura, secretos y migraciones sobre la BD de producción (respaldado por ADR-github-actions-deploy-produccion-pipeline-y-secretos). No se mergea automáticamente.
