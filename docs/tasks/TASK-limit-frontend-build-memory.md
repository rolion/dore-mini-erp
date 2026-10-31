# TASK-limit-frontend-build-memory: Bound Angular production build memory
**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** NO
**Rama:** task/TASK-limit-frontend-build-memory
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/45

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-31 | (nuevo) → INVESTIGATION → PLANNING | Actual droplet build failed; user requested single-worker1536MiB setting | delivery-start |

## Investigación
### Requerimiento
Production Angular compiler worker failed with JS heap out of memory on droplet. User reports961MiB RAM,558MiB available,2GiB swap (1.8GiB available), and explicitly suggests NG_BUILD_MAX_WORKERS=1 NODE_OPTIONS=--max-old-space-size=1536 for the production build.
### Hechos encontrados
- frontend/panel_admin/Dockerfile:7 invokes production build without resource settings.
- Installed @angular/build/src/utils/environment-options.js:101-110 supports NG_BUILD_MAX_WORKERS and defaults up to4workers.
- Installed compiler parallel-compilation.js:33 uses a separate worker; NODE_OPTIONS sets inherited V8 heap policy.
- Supplied build log reports worker heap termination, not Sass warning failure.
- PR44 merged to main at ebdfbb0; this is a new follow-up task, preserving original PR.
### Hipótesis / supuestos no confirmados
Single worker1536MiB heap is an appropriate retry, not a guarantee that this host can build alongside existing services. Heap cap is not total process memory or physical RAM allocation.
### Módulos / comportamiento / restricciones
Docker build only. Existing topology/production artifact unchanged. Do not read dotenv, change packages, production services, migrations or droplet. No local dependency installs.
### Veredicto
NEEDS_PLAN — bounded build configuration and operator documentation, no new architectural decision.
### Diseño requerido
NO — no UI changes.
## Diseño
Not applicable.
## Arquitectura
Existing ADR-docker-production-deployment-proxy-and-database remains valid; no new topology decision.
## Plan
PLAN-2026-10-31-limit-frontend-build-memory.md v1, COMPACTO, READY.
## Implementación
Dockerfile ARG defaults NG_BUILD_MAX_WORKERS=1 and NODE_OPTIONS=--max-old-space-size=1536 applied only to compile RUN. README/runbook document serial builds, override, heap/total memory distinction and actual host limitations. Developer frontend Docker build passed; compilation step34.2s, final image b8b7835d912f. No application/package/backend changes. Independent review pending.
## Review
PASS — independent memory_build_review, commit00f657f, no findings. Production build succeeded; final image has no build-only flags; Nginx syntax/index valid. See docs/reviews/QA-2026-10-31-limit-frontend-build-memory.md. Actual1GiB droplet remains unverified.
## Publicación
PR45 ready for human review; no merge or deployment.