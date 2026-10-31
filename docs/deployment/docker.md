# Production Docker deployment

This stack builds two images: Django/Gunicorn and Angular production/Nginx. Existing nginx-proxy terminates HTTPS and routes both www.pocketbiz.website and app.pocketbiz.website to frontend port 80. Frontend serves the SPA, forwards /api and /admin to backend, and serves collected Django static files. No host ports, database service or replacement public proxy are created.

## Host prerequisites

Use Docker Engine with the Compose v2 plugin on the droplet. Check DNS A records for both domains point at the droplet (and any AAAA record reaches it), ports 80/443 reach the existing proxy, and the proxy/acme volumes/socket configuration already works.

Discover the existing PostgreSQL network, without exposing credentials:

```sh
docker inspect db_v2 --format '{{range $name, $_ := .NetworkSettings.Networks}}{{$name}} {{end}}'
docker network inspect proxy --format '{{.Name}}'
```

Choose an existing network on db_v2 which resolves db_v2. Keep it and proxy restricted to trusted containers: production Django trusts X-Forwarded-Proto. Backend joins the database network and project app network; frontend joins app and proxy.

## Runtime configuration

Export these in the deployment shell through your normal secret management. Do not put actual secrets in the repository or Docker build arguments:

```sh
export DATABASE_NETWORK='replace-with-existing-db-network'
export DATABASE_URL='postgresql://USER:URL_ENCODED_PASSWORD@db_v2:5432/APP_DATABASE'
export SECRET_KEY='replace-with-a-long-random-production-secret'
export IMAGE_TAG='replace-with-immutable-release-tag'
# Optional: TIME_ZONE (default America/La_Paz), REGISTRATION_ENABLED (default True)
```

The application database/user must already exist; use a dedicated least-privilege database role. URL-encode reserved characters in credentials. No secrets are baked into either image. Compose requires all three DATABASE_NETWORK, DATABASE_URL and SECRET_KEY. ALLOWED_HOSTS and proxy/certificate domains are fixed to the requested two domains. Django DEBUG stays False.

VIRTUAL_HOST and LETSENCRYPT_HOST are www.pocketbiz.website,app.pocketbiz.website (comma separated without spaces); LETSENCRYPT_EMAIL is joe.doe@pocketbiz.com. Change this address in compose.yaml before rollout if it is only an example address.

## Build and first deployment

From the repository root:

```sh
# Validate without printing rendered environment/credentials.
docker compose config --quiet
docker compose build --pull
# Back up the application database with your existing host backup procedure first.
docker compose run --rm --no-deps backend python manage.py migrate --noinput
docker compose up -d --wait
docker compose ps
docker compose logs --tail=100 backend frontend
```

Build installs the declared Python/npm packages inside build stages. Backend starts as UID 10001, collects static files into a named volume, then runs two Gunicorn workers. Frontend starts after backend liveness is healthy and mounts the volume read-only. The health API checks process availability, not database readiness. Migrations run only when explicitly requested above. Do not run migrations against an unrelated application's database.

If an admin account is needed:

```sh
docker compose exec backend python manage.py createsuperuser
```

A superuser still needs a company assignment for business API access (see CLAUDE.md). Regular registration creates a company through the existing flow.

## Smoke checks

Run after certificates have been issued:

```sh
curl --fail https://www.pocketbiz.website/api/health/
curl --fail https://app.pocketbiz.website/api/health/
curl --fail -I https://app.pocketbiz.website/pocketbiz/login
curl --fail -I https://app.pocketbiz.website/admin/login/
curl --fail -I https://app.pocketbiz.website/static/admin/css/base.css
# Expect 404, never the SPA HTML:
curl -I https://app.pocketbiz.website/assets/does-not-exist.js
curl -I https://app.pocketbiz.website/api/does-not-exist/
```

Confirm health JSON, both certificate hostnames, deep-route refresh, admin styling and successful admin login/CSRF. API errors must remain Django responses. Browser-check a normal login and one read against the existing database. If HTTPS loops, verify the outer proxy overwrites forwarded protocol and frontend preserves it; keep SECURE_SSL_REDIRECT enabled.

## Updates and rollback

Keep old image tags available. Back up PostgreSQL before explicit migrations. Build a new immutable IMAGE_TAG, run migration only if needed, then compose up. Nginx uses Docker DNS dynamically; restart frontend after backend replacement if troubleshooting stale connections.

To revert application images, export the previous IMAGE_TAG then run:

```sh
docker compose up -d --no-build --wait
```

This task adds no migrations. Future schema changes need their own backwards-compatibility or restore plan; image rollback alone does not undo migrations. Never use docker compose down -v: that would delete collected static data. External PostgreSQL/proxy resources are not owned by this stack. No command here stops the existing db_v2 or proxy containers.

## Verification limits

Compose interpolation can be validated without a daemon. Image builds, Nginx syntax checks and runtime routing/health checks require Docker running. Complete those checks before approving or deploying this change.