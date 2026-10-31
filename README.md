# PocketBiz

Mini ERP with a Django/DRF backend and Angular frontend.

## Manual production deployment

Run these commands in a Linux shell on the deployment host, from the repository root. The stack builds two images: a production Django/Gunicorn backend and an Angular production build served by Nginx.

### Prerequisites

- Docker Engine and Docker Compose v2 or newer.
- Existing PostgreSQL container `db_v2`, with an application database and database user already created.
- Existing nginx-proxy/docker-gen/acme-companion connected to external Docker network `proxy`.
- DNS for `www.pocketbiz.website` and `app.pocketbiz.website` points to the droplet; ports 80/443 reach the existing proxy. Check any IPv6 records as well.
- A database backup before applying migrations.

No new PostgreSQL or public proxy container is created. Only frontend joins the public proxy network. Backend and frontend communicate through a private application network; neither publishes host ports.

### 1. Get the code and identify the database network

Check out the release you intend to deploy, then run:

```sh
docker version
docker compose version
docker network inspect proxy --format '{{.Name}}'
docker inspect db_v2 --format '{{range $name, $_ := .NetworkSettings.Networks}}{{$name}} {{end}}'
```

Use an existing network attached to `db_v2` for `DATABASE_NETWORK`. The database hostname must resolve on that network. Keep these networks restricted to trusted containers.

### 2. Set production configuration

Set the following through your usual secret-management process in the same shell that will run Compose. Replace every placeholder; do not commit real credentials or pass them as image build arguments.

```sh
export DATABASE_NETWORK='replace-with-existing-database-network'
export DATABASE_URL='postgresql://USER:URL_ENCODED_PASSWORD@db_v2:5432/APP_DATABASE'
export SECRET_KEY='replace-with-a-long-random-production-secret'
export IMAGE_TAG='replace-with-immutable-release-tag'
```

URL-encode special characters in database credentials. Use a dedicated database user with permissions on the application database. Optional settings are `TIME_ZONE` (default `America/La_Paz`) and `REGISTRATION_ENABLED` (default `True`). Django runs with `DEBUG=False`.

The frontend has these settings in `compose.yaml`:

```yaml
VIRTUAL_HOST: www.pocketbiz.website,app.pocketbiz.website
LETSENCRYPT_HOST: www.pocketbiz.website,app.pocketbiz.website
LETSENCRYPT_EMAIL: joe.doe@pocketbiz.com
VIRTUAL_PORT: "80"
```

Confirm the certificate email is an address you intend to use before deployment.

### 3. Build the production images

```sh
docker compose config --quiet
docker compose build --pull
```

Builds install Python/npm dependencies inside Docker. The frontend runs `npm ci` and `ng build --configuration production`, then copies the compiled files into Nginx. No local Python or Node installation is needed on the droplet. The build needs access to image/package registries and the Google Fonts URLs referenced by the existing frontend.

### 4. Apply migrations and start

Back up the application database using the host's existing backup procedure. Confirm `DATABASE_URL` targets the correct application database, then run:

```sh
docker compose run --rm --no-deps backend python manage.py migrate --noinput
docker compose up -d --wait
docker compose ps
docker compose logs --tail=100 backend frontend
```

Migrations are explicit and do not run on container restart. Backend startup collects Django static files into a shared volume, then starts Gunicorn as a non-root user. Frontend starts after backend is healthy and serves those static files read-only.

For an initial Django admin account, if needed:

```sh
docker compose exec backend python manage.py createsuperuser
```

A Django superuser needs a company assignment to access business API data. The regular registration flow creates a company.

### 5. Verify the deployment

Wait for the existing certificate companion to issue certificates, then run:

```sh
curl --fail https://www.pocketbiz.website/api/health/
curl --fail https://app.pocketbiz.website/api/health/
curl --fail -I https://app.pocketbiz.website/pocketbiz/login
curl --fail -I https://app.pocketbiz.website/admin/login/
curl --fail -I https://app.pocketbiz.website/static/admin/css/base.css
# These must return 404, not the SPA index:
curl -I https://app.pocketbiz.website/assets/does-not-exist.js
curl -I https://app.pocketbiz.website/api/does-not-exist/
```

Open the app in a browser: check login, refresh a deep route, confirm admin styling and login, and read application data. The health endpoint reports process liveness, not database readiness. HTTPS must not enter a redirect loop.

### Updates and rollback

Use a new immutable `IMAGE_TAG` for each release, retain the previous images, and repeat build, backup, migration (if needed), start and smoke checks.

To restore previous application images:

```sh
export IMAGE_TAG='previous-release-tag'
docker compose up -d --no-build --wait
```

Image rollback does not undo database migrations: assess schema compatibility or use the database restore plan. Do not run `docker compose down -v`; it removes the stack's static volume. PostgreSQL and the public proxy remain externally managed.

See [the deployment runbook](docs/deployment/docker.md) for additional operational details. Development commands and project conventions are in [CLAUDE.md](CLAUDE.md).