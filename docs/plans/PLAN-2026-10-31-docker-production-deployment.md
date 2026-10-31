# PLAN-2026-10-31-docker-production-deployment (v5)

**Task:** TASK-docker-production-deployment · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** ADR-docker-production-deployment-proxy-and-database

## Objective
Build/run two production application containers on the supplied droplet, reusing proxy/PostgreSQL.
## Context
See TASK investigation and ADR. No business context, payload or screen layout changes. User explicitly requested resolution of REV-01/02, confirmed PocketBiz title and authorized npm vulnerability remediation.

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
- **AC-06:** The application browser title is PocketBiz; root-shell tests reflect the standalone app rather than the old Oreva demo and the frontend regression suite passes.
- **AC-07:** Full npm audit and production-only npm audit report zero known vulnerabilities; remove unused vulnerable packages, update compatible dependencies and document any narrowly scoped overrides.

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
| AC-06 | Root shell/title tests, frontend full Karma regression suite |
| AC-07 | Online full and production-only npm audit, locked npm ci, production build/lint and updated container smoke checks |
| AC-05 | Config/startup/runbook review and container health/startup checks |

## E2E
NO business-flow E2E: no workflow changes. Container HTTP smoke checks are deployment integration checks. Record unavailable checks and do not issue PASS while applicable checks are missing.
## Regression tests
Relevant backend configuration tests, frontend build/lint. Publisher records unavailable broader tests/security tools.

# Implementation Plan
## Architecture considerations
Follow linked ADR and modular monolith. No domain/contract changes.
## Files/components affected
Frontend angular.json test polyfills, src/testing template-provider helper, legacy smoke test setup, demo button radio bindings; tools/minimatch-compat adapter and compatibility tests; root compose.yaml; backend Dockerfile/.dockerignore/.gitattributes/docker-entrypoint.sh/requirements/production.txt/config/settings/production.py and targeted configuration tests; frontend/panel_admin Dockerfile/.dockerignore/nginx.conf and package.json/package-lock.json; frontend/panel_admin/src/app/app.component.ts and app.component.spec.ts plus additional existing test harness fixes required to restore the regression suite; README.md, docs/deployment/docker.md and delivery artifacts.
## Implementation steps
1. Backend production image/startup/static/proxy settings (AC-01/03/04).
2. Locked Angular image and Nginx routing (AC-01/04).
3. Compose runtime/network/volume/health configuration (AC-02/03/05).
4. Configuration regression tests and runbook (AC-03/04/05).
5. Resolve REV-01: preserve PocketBiz title, replace obsolete Oreva app tests with standalone shell/title checks; correct any subsequently exposed existing test harness setup failures without weakening business assertions (AC-06).
6. Resolve REV-02: remove unused vulnerable xlsx/browser-sync, update ECharts and Angular21/tooling packages to patched compatible releases, refresh lockfile; use a documented local callable-API adapter backed by minimatch11.0.3 and override modern glob to14.0.3 while preserving legacy Glob7 callbacks (AC-07).
7. Run full frontend tests/lint/build/audits, locked container rebuild and runtime smoke; independent delivery-publish review.
## Database / migrations
No schema changes; existing migrations run manually after backup.
## Risks
Unknown host DB network; require discovery. Docker stopped locally prevents image/runtime checks.
## New dependencies
Gunicorn production image only. No local install planned. Notify before image builds install declared Python/npm packages; no testing dependency added.

## Changelog
- **v2** (2026-10-31): [Implementation Plan] Add root README.md with manual production instructions, explicitly requested by user. Acceptance criteria unchanged; expands AC-05 documentation.
- **v3** (2026-10-31): [Specification] User explicitly approved review remediation in this chat: PocketBiz title, resolve stale tests and npm audit vulnerabilities (AC-06/07). [Implementation Plan] Expand frontend manifest/lock/app-shell tests and related test harness fixes; remove unused vulnerable packages, update compatible release lines, document overrides and rerun quality gate. No new business behavior, UI layout, database or infrastructure decision.
- **v4** (2026-10-31): [Implementation Plan] Remaining advisories affect legacy minimatch consumers in Karma/ESLint. Use private local adapter delegating every match/class/helper to minimatch11.0.3, with callable API compatibility tests, and glob>=9 override14.0.3. Copy adapter before npm ci in Docker. Regenerate stale nested lock resolution through a clean lock install; no advisory suppressions, force downgrades or custom pattern engine. Specification unchanged.
- **v5** (2026-10-31): [Implementation Plan] Full suite now executes and exposed inherited smoke-test missing providers/localization, one standalone declaration, external Google Maps dependency and removed ng-bootstrap radio-group accessor. Supply scoped template test services/localize polyfill, shallow the external SDK boundary, and use native Angular radio bindings with interaction regression checks. Preserve business assertions and screen layout. Adapter additionally supplies Glob7 segment metadata through nonrecursive Matcher.test and legacy Windows absolute path handling. Specification unchanged.