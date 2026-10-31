# PLAN-2026-10-31-limit-frontend-build-memory (v1)
**Task:** TASK-limit-frontend-build-memory · **Modo:** COMPACTO · **Specification readiness:** READY
**DDRs / ADRs:** Existing deployment ADR; no new decision.
## Objective
Apply the user's single-worker1536MiB Angular build setting, allowing larger build hosts to override it.
# Specification
- **Expected behavior:** Production compilation uses NG_BUILD_MAX_WORKERS=1 and NODE_OPTIONS=--max-old-space-size=1536 by default. Docker build args may override either. Settings affect only compilation, not final Nginx runtime or npm dependency resolution.
- **AC-01:** Default frontend Docker build completes with explicit settings; overrides supported; final runtime contains no NODE_OPTIONS/NG_BUILD_MAX_WORKERS.
- **AC-02:** README/runbook explain heap-vs-total-memory, serial retry, override command and alternative build host if memory remains insufficient; no guarantee on actual1GiB droplet.
- **Edge/error cases:** Exit137/kernel OOM differs from V8 heap error. Raising heap does not add RAM. Shell exports alone are not automatically forwarded into Docker.
- **Out of scope:** Droplet swap/RAM changes, dependency/source/UI/backend changes, changing public proxy/database resources.
# Test Specification
AC-01: execute frontend Docker build, inspect final image environment/static output/Nginx syntax; override build arg plumbing by Dockerfile inspection. AC-02: command/document review against actual Dockerfile. Existing1060test/audit baseline unchanged; no frontend test rerun needed for build-only change. E2E:NO, no user workflow change.
# Implementation Plan
- **Files:** frontend/panel_admin/Dockerfile; README.md; docs/deployment/docker.md; task/plan/review.
- **Steps:** Add ARG defaults and inline build-step environment; document retry/override and host limits; build frontend; independent review, same new PR.
- **Risks / New dependencies:** No new dependencies. Docker build installs existing declared packages in image if uncached. Host low-memory behavior can only be confirmed by user retry; local build success is not identical hardware verification.