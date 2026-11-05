# Deploy automático con GitHub Actions

Cada push a `main` (merge de un PR) ejecuta `.github/workflows/deploy.yml`, que: construye las imágenes en el runner de GitHub, las carga en el droplet por SSH, respalda la BD, corre `migrate` y levanta la nueva versión; al final verifica `/api/health/`. También se puede lanzar a mano desde *Actions → Deploy → Run workflow* (solo se despliega desde `main`; sirve para re-desplegar). Decisión: `docs/adr/ADR-github-actions-deploy-produccion-pipeline-y-secretos.md`.

## Configuración única (antes del primer merge)

En GitHub: *Settings → Environments → New environment* `production` (opcional: *Required reviewers* para exigir aprobación manual en cada deploy). Cargar ahí:

**Secrets**

| Nombre | Contenido |
|---|---|
| `DEPLOY_SSH_KEY` | Llave privada SSH dedicada al deploy |
| `DEPLOY_KNOWN_HOSTS` | Salida de `ssh-keyscan -t ed25519 <host>` ejecutada desde un lugar de confianza |
| `SECRET_KEY` | `SECRET_KEY` de Django en producción |
| `DB_USER` | Usuario de la BD de la aplicación (mínimo privilegio) |
| `DB_PASSWORD` | Contraseña de ese usuario (se codifica sola para la URL) |
| `DB_NAME` | Nombre de la base de datos |

**Variables**

| Nombre | Contenido |
|---|---|
| `DEPLOY_HOST` | IP o dominio del droplet |
| `DEPLOY_USER` | Usuario SSH (debe poder usar `docker`) |
| `DEPLOY_PATH` | Ruta absoluta de despliegue, p. ej. `/opt/pocketbiz` |
| `DATABASE_NETWORK` | Red Docker existente que resuelve `db_v2` |
| `DB_HOST` (opc.) | Host de la BD, por defecto `db_v2` |
| `DB_PORT` (opc.) | Por defecto `5432` |
| `DB_CONTAINER` (opc.) | Contenedor de PostgreSQL para `pg_dump`, por defecto `db_v2` |
| `TIME_ZONE`, `REGISTRATION_ENABLED` (opc.) | Ver `docker.md` |
| `HEALTH_URL` (opc.) | Por defecto `https://www.pocketbiz.website/api/health/` |

Recomendado: en el environment `production`, restringir *Deployment branches* a `main`.

`DATABASE_URL` no se guarda: se compone de `DB_USER`, `DB_PASSWORD` y `DB_NAME`. El workflow falla al inicio si falta algo.

## Llave SSH de deploy

```sh
ssh-keygen -t ed25519 -f deploy_key -C "github-deploy" -N ""
```

Añadir `deploy_key.pub` a `~/.ssh/authorized_keys` del usuario de deploy en el droplet, cargar `deploy_key` en `DEPLOY_SSH_KEY` y borrar ambos archivos locales. El usuario debe pertenecer al grupo `docker`. La cuenta de la BD debe poder hacer `pg_dump` de su base (si no, el backup falla y el deploy se aborta sin migrar).

## Qué hace en el servidor

1. Backup `pg_dump` comprimido en `$DEPLOY_PATH/backups/` (últimos 10); si falla, **no migra**.
2. `docker compose run --rm --no-deps backend python manage.py migrate --noinput`; si falla, los contenedores en ejecución no se tocan.
3. `docker compose up -d --no-build --wait`.
4. Poda imágenes antiguas conservando las últimas 5 releases (tag = SHA de 12 caracteres).

## Rollback

- Revertir el commit en `main` (el push redespliega), o en el droplet: `IMAGE_TAG=<sha previo> docker compose up -d --no-build --wait` (con las variables de `docker.md` exportadas).
- Volver de imagen no deshace migraciones. Si una migración fue destructiva, restaurar el backup más reciente de `$DEPLOY_PATH/backups/` (`gunzip -c … | docker exec -i db_v2 psql -U USER DB`) tras evaluar el impacto.
- Nunca `docker compose down -v`.

## Límites

No hay gate de tests: un merge a `main` roto se despliega. Se recomienda proteger `main` y añadir un workflow de tests como task aparte.
