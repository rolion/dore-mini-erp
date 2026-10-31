# TASK-docker-production-deployment: Production Docker deployment

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** NO
**Rama:** task/TASK-docker-production-deployment
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/44

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-31 | ENGINEERING → REVIEW | Implementation complete; independent gate pending | delivery-build |
| 2026-10-31 | (nuevo) → INVESTIGATION → ARCHITECTURE → PLANNING | Investigation, ADR and READY specification | delivery-start |

## Investigación
### Requerimiento
Build backend and Angular production images with Compose for a DigitalOcean droplet. Serve Angular through Nginx. Reuse existing PostgreSQL 16 container db_v2 and nginx-proxy/docker-gen/acme-companion on external network proxy. Frontend must advertise www.pocketbiz.website,app.pocketbiz.website for VIRTUAL_HOST and LETSENCRYPT_HOST, with LETSENCRYPT_EMAIL joe.doe@pocketbiz.com.
### Hechos encontrados
- backend/config/wsgi.py:14 defaults to production settings.
- backend/config/settings/production.py:5-13 requires database URL, secret and hosts, enables HTTPS redirect, but lacks proxy HTTPS handling.
- backend/requirements/base.txt:1-4 has no production WSGI server.
- frontend/panel_admin/src/environments/environment.ts:3 uses same-origin /api.
- frontend/panel_admin/angular.json:20-21,67-95 defines application-builder production output dist/oreva.
- backend/config/urls.py:9-27 exposes admin and API; backend/config/health.py:6-9 provides public liveness.
- backend/config/settings/base.py:81 defines static URL but no collection root.
- docs/adr/ADR-landing-pocketbiz-rutas-url-sin-hash.md requires SPA fallback excluding API/admin/static.
- No deployment files exist. Docker daemon unavailable locally. gh CLI unauthenticated; connector available. Git fetch succeeded.
- Existing untracked npm lockfile available: include unchanged for reproducible builds. Unrelated deleted skill links and design exports must remain untouched.
### Hipótesis / supuestos no confirmados
DB network name/credentials unknown: require operator values. Operator manages DNS/proxy.
### Módulos y dependencias relacionadas
Infrastructure, production Django settings and Angular build; no business modules.
### Implementaciones similares existentes
Production settings and clean-route ADR above.
### Comportamiento actual
Development servers only; no versioned deployment.
### Restricciones
Do not read/change .env or secrets, migrations or unrelated work. No droplet deployment. No new local dependency install without confirmation.
### Riesgos identificados
HTTPS redirect loops, missing admin static files, unknown DB network, unavailable Docker runtime.
### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — New deployment infrastructure and external network integration.
### Diseño requerido
**NO** — No visual changes.

## Diseño
Not applicable.
## Arquitectura
docs/adr/ADR-docker-production-deployment-proxy-and-database.md
## Plan
docs/plans/PLAN-2026-10-31-docker-production-deployment.md (v1), COMPLETO, Specification readiness: READY.
## Implementación
Two production images and Compose implement AC-01/02/03/05. Nginx SPA/API/admin/static routing and production proxy/static settings implement AC-04. Added five isolated settings tests without reading dotenv or requiring PostgreSQL; deployment guide covers all operator steps.
Existing npm lockfile included unchanged. Added backend/.gitattributes to ensure the Linux entrypoint keeps LF line endings after Windows checkout (implementation detail). Gunicorn pinned to 26.2.0, verified on PyPI; no local package installation. No domain/UI/schema changes.
Developer checks: five settings tests pass; Compose valid configuration and all three required-variable rejection checks pass; frontend lint passes. Production build retry running after sandbox blocked Google Fonts. Docker engine unavailable despite Desktop application being present.
## Review
Pending.
## Publicación
Pending.
