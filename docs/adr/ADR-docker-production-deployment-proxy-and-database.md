# ADR-docker-production-deployment-proxy-and-database: Two images behind existing infrastructure

**Estado:** Propuesto
**Task relacionado:** TASK-docker-production-deployment
**Fecha:** 2026-10-31

## Contexto
Existing proxy terminates TLS; PostgreSQL already runs. Angular calls /api and requires clean-route fallback. Django needs HTTPS awareness and admin static files.

## Decisión
Two services: Python 3.12/Gunicorn backend, multi-stage Node 22 production build/Nginx frontend. Only frontend joins external proxy and advertises domains. No published host ports. Both share a project-scoped app network; backend alone joins required external DATABASE_NETWORK. DATABASE_URL references existing db_v2, with no new DB service/volume.

Frontend serves SPA, forwards /api and /admin unchanged, serves Django collected static files from a read-only named volume. Missing assets return 404. Backend collects static files then runs Gunicorn as non-root. Migrations are an explicit operator command, never automatic on restart. Required secrets are runtime environment values, excluded from build contexts.

Production Django trusts forwarded HTTPS. Frontend validates the incoming forwarded protocol and preserves it from the existing proxy. Backend has no public port; external networks must contain only trusted containers. Health probes supply configured host/HTTPS headers.

Commit existing npm lockfile unchanged for npm ci. Add Gunicorn only to production requirements; no local installation needed.

## Alternativas consideradas
Separate public backend hostname adds DNS/TLS/CORS without need. Duplicating PostgreSQL/proxy risks host/data conflicts. Python static middleware adds a dependency where Nginx already suffices. Automatic migrations couple restart to schema changes.

## Estrategia de rollback / mitigación
Use immutable release image tags and retain old images; back up PostgreSQL before explicit migrations. Redeploy previous image tag with --no-build, restarting frontend after backend recreation for DNS resolution. No schema changes introduced here. Never down -v. External proxy/DB remain owned by the host. Future schema rollback needs separate compatibility/restore assessment.

## Consecuencias
Two images, same-origin routing, shared static volume populated before frontend starts. Runtime image/HTTP checks require Docker; unavailable checks must remain explicit and block PASS.

## Sources
- [External networks](https://docs.docker.com/compose/how-tos/networking/)
- [nginx-proxy](https://github.com/nginx-proxy/nginx-proxy/blob/main/docs/README.md)
- [acme-companion](https://github.com/nginx-proxy/acme-companion/wiki/Basic-usage)
- [Django HTTPS headers](https://docs.djangoproject.com/en/5.2/ref/settings/#secure-proxy-ssl-header)
