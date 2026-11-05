# PLAN-2026-11-05-github-actions-deploy-produccion (v1)

**Task:** TASK-github-actions-deploy-produccion · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** ADR-github-actions-deploy-produccion-pipeline-y-secretos (respeta ADR-docker-production-deployment-proxy-and-database)

## Objective
Automatizar el deploy: cada push a `main` construye las imágenes, respalda la BD, corre las migraciones y levanta la nueva versión en el droplet, con credenciales inyectadas desde GitHub.

## Context
Ver TASK. El deploy manual está en `docs/deployment/docker.md`.

# Specification

## Current behavior
Deploy manual (`docs/deployment/docker.md`); sin `.github/`. Las migraciones son explícitas (`backend/docker-entrypoint.sh:4-5`).

## Expected behavior
- Un push a `main` (merge de PR) o un `workflow_dispatch` ejecuta el workflow `Deploy` en el environment `production`.
- Las imágenes se construyen con tag = SHA corto y se cargan en el droplet; las migraciones corren una vez con la imagen nueva antes de reemplazar contenedores.
- Las credenciales de BD y `SECRET_KEY` provienen exclusivamente de GitHub Secrets/Variables.

## Domain rules / invariants
- INV-01: nunca se migra sin backup previo exitoso.
- INV-02: si migrar falla, no se reemplazan los contenedores en ejecución.
- INV-03: ningún secreto se escribe en el repo, en imágenes ni en disco del droplet.
- INV-04: un solo deploy a la vez; los deploys no se cancelan a mitad.
- INV-05 (heredada): no `down -v`; no se toca la BD ni el proxy externos.

## Acceptance criteria
- AC-01: existe `.github/workflows/deploy.yml` disparado por `push` a `main` y `workflow_dispatch`, con `concurrency` sin `cancel-in-progress`, `permissions: contents: read` y `environment: production`.
- AC-02: el workflow construye ambas imágenes con `pocketbiz-backend:<sha>` / `pocketbiz-frontend:<sha>` y las carga en el droplet por SSH verificando host key.
- AC-03: `DATABASE_URL` se compone desde `DB_USER`, `DB_PASSWORD` (codificada como URL) y `DB_NAME`; falla con mensaje claro si falta cualquier secret/variable requerida.
- AC-04: el script remoto hace backup (aborta si falla), migra con `run --rm --no-deps`, luego `up -d --no-build --wait`, y conserva las últimas N releases e imágenes.
- AC-05: tras el deploy el workflow verifica `/api/health/` y falla si no responde.
- AC-06: `docs/deployment/github-actions.md` lista cada secret/variable, cómo crear la llave SSH de deploy y el usuario/permiso, cómo hacer rollback, y `docs/deployment/docker.md` lo referencia.

## Edge cases / Error cases
- Falta una variable requerida → falla temprano, antes de construir o conectar.
- `pg_dump` falla → abort, sin migrar.
- Migración falla → abort, versión anterior sigue sirviendo.
- Healthcheck falla → job rojo; rollback documentado.
- Dos merges seguidos → el segundo espera (concurrency).
- Contraseña con caracteres reservados → codificada.

## Authorization / permissions
Llave SSH dedicada al deploy; usuario del droplet con acceso a Docker y sin privilegios extra. Se recomienda aprobación requerida en el environment y protección de `main`. Workflow con permisos de solo lectura.

## Non-functional requirements
Sin dependencias nuevas de npm/pip; solo `actions/checkout` oficial. Build en runner (no en el droplet).

## Out of scope
Gate de tests/CI de PRs, GHCR, notificaciones, restore automático, cambio de `compose.yaml` o de los Dockerfiles, staging.

## Open questions (no bloquean)
Nombre real del contenedor/usuario SSH/ruta de deploy: se parametrizan por variables con los defaults documentados.

# Test Specification

## Unit tests / Integration tests
- `scripts/deploy/test_remote_deploy.sh` (o test Python junto a `backend/config/test_production_deployment.py`): valida el script con `bash -n`, la composición/codificación de `DATABASE_URL` y la falla por variables faltantes (modo `--check`/dry-run sin Docker).
- Validación estática del YAML (`python -c yaml.safe_load`) y de las claves de AC-01 con un test.

## E2E
**NO** — requiere el droplet real; se verifica en el primer merge a `main` (checklist en la guía).

## Regression tests
`python manage.py test config` (incluye `test_production_deployment.py`) sigue verde; `docker compose config --quiet` con variables dummy.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | test de estructura del YAML |
| AC-02 | revisión del workflow + test de estructura (tags, known_hosts) |
| AC-03 | test del script en modo check (URL, codificación, variables faltantes) |
| AC-04 | `bash -n` + test de orden de pasos en dry-run; revisión |
| AC-05 | test de estructura (paso de smoke presente) |
| AC-06 | revisión de docs + enlace desde `docker.md` |

# Implementation Plan

## Architecture considerations
Ver ADR. Build en runner, transferencia `docker save | ssh docker load`, ejecución remota por stdin.

## Proposed solution
Workflow + script remoto versionado (`scripts/deploy/remote-deploy.sh`) que se copia al droplet y se ejecuta con las variables en el entorno.

## Files/components affected
- Nuevos: `.github/workflows/deploy.yml`, `scripts/deploy/remote-deploy.sh`, `docs/deployment/github-actions.md`, test del script.
- Editados: `docs/deployment/docker.md` (enlace), `CLAUDE.md` (una línea sobre el deploy).
- Sin cambios en backend, frontend, migraciones ni `compose.yaml`.

## Implementation steps
1. Script remoto con validación de variables, `DATABASE_URL` codificada, backup + retención, migrate, up, poda (INV-01..03, AC-03, AC-04).
2. Workflow (AC-01, AC-02, AC-05).
3. Tests del script y del workflow.
4. Guía y enlaces (AC-06).

## Database / migrations
No se crean migraciones; el pipeline ejecuta `migrate` de las existentes.

## Risks
Supuestos del droplet (nombre de contenedor, permisos `pg_dump`); migraciones no reversibles; sin gate de tests; los secrets los debe cargar la persona administradora antes del primer merge.

## New dependencies
Ninguna (solo `actions/checkout`).
