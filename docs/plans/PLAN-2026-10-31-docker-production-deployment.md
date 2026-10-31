# PLAN-2026-10-31-docker-production-deployment (v1)

**Task:** TASK-docker-production-deployment · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** ADR-docker-production-deployment-proxy-and-database

## Objective
Build/run two production application containers on the supplied droplet, reusing proxy/PostgreSQL.
## Context
See TASK investigation and ADR. No business context, payload or screen changes.

# Specification
## Current behavior
Angular environment.ts:3 calls /api. backend/config/urls.py:9-27 serves API/admin. production.py:5-13 requires runtime variables. No Docker deployment.
## Expected behavior
Compose builds Django/Gunicorn and Angular/Nginx images. Frontend owns domain registration. Database and public proxy remain external.
## Acceptance criteria
- **AC-01:** Both images build; Angular production uses committed lockfile; backend Gunicorn runs non-root with production settings.
- **AC-02:** Frontend joins external proxy with VIRTUAL_HOST and LETSENCRYPT_HOST www.pocketbiz.website,app.pocketbiz.website, LETSENCRYPT_EMAIL joe.doe@pocketbiz.com and VIRTUAL_PORT 80. No published ports/new proxy or DB.
- **AC-03:** Backend joins required external DATABASE_NETWORK and requires DATABASE_URL/SECRET_KEY. Missing variables fail interpolation. Build contexts exclude credentials/env files.
- **AC-04:** SPA deep routes work; API/admin reach Django; collected static assets load; missing assets return 404. HTTPS forwarding avoids loops and preserves same-origin CSRF.
- **AC-05:** Restart policies, liveness probes and ordered static collection exist. Migrations explicit. Runbook covers discovery, DNS/secrets, backup, build/deploy, smoke tests and rollback.
## Edge cases / Error cases
Missing external network fails instead of creating one. DB health is distinct from liveness. Missing assets cannot become SPA HTML. Frontend restart required after backend recreation. No automatic migrations/volume deletion.
## Authorization / permissions
Existing permissions/company isolation unchanged. Trusted Docker networks only; backend has no public port.
## Non-functional requirements
Exclude env/caches/local dependencies. Non-root backend; pinned production server dependency. No local dependency installs without confirmation.
## Out of scope
Droplet/DNS/proxy changes, database creation, registry CI, domain code, schema and visual changes.

# Test Specification
## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | Docker builds, production Angular build and Dockerfile review |
| AC-02 | Compose config with synthetic values; inspect networks/variables/ports |
| AC-03 | Required-variable negative checks, context exclusion review, synthetic production settings checks |
| AC-04 | Targeted production-settings regression tests; Nginx syntax/container HTTP smoke tests for API/admin/SPA/static |
| AC-05 | Config/startup/runbook review and container health/startup checks |

## E2E
NO business-flow E2E: no workflow changes. Container HTTP smoke checks are deployment integration checks. Record unavailable checks and do not issue PASS while applicable checks are missing.
## Regression tests
Relevant backend configuration tests, frontend build/lint. Publisher records unavailable broader tests/security tools.

# Implementation Plan
## Architecture considerations
Follow linked ADR and modular monolith. No domain/contract changes.
## Files/components affected
Root compose.yaml; backend Dockerfile/.dockerignore/docker-entrypoint.sh/requirements/production.txt/config/settings/production.py and targeted configuration tests; frontend/panel_admin Dockerfile/.dockerignore/nginx.conf and existing package-lock.json; docs/deployment/docker.md and delivery artifacts.
## Implementation steps
1. Backend production image/startup/static/proxy settings (AC-01/03/04).
2. Locked Angular image and Nginx routing (AC-01/04).
3. Compose runtime/network/volume/health configuration (AC-02/03/05).
4. Configuration regression tests and runbook (AC-03/04/05).
5. Run specified checks; independent delivery-publish review.
## Database / migrations
No schema changes; existing migrations run manually after backup.
## Risks
Unknown host DB network; require discovery. Docker stopped locally prevents image/runtime checks.
## New dependencies
Gunicorn production image only. No local install planned. Notify before image builds install declared Python/npm packages; no testing dependency added.
