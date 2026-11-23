# PLAN-2026-11-23-configurar-dependabot-actualizaciones (v1)

**Task:** TASK-configurar-dependabot-actualizaciones · **Modo:** COMPACTO · **Specification readiness:** READY
**DDRs / ADRs:** Ninguno

## Objective
Que GitHub vigile semanalmente las dependencias del proyecto y abra PRs de actualización (y de seguridad), agrupados para no saturar, sin tocar el deploy ni el código de producto.

# Specification
- **Expected behavior:** existe `.github/dependabot.yml` válido que cubre cuatro ecosistemas, con ejecución semanal, límite de PRs abiertos y agrupación de minor/patch.
- **Acceptance criteria:**
  - AC-01: ecosistemas cubiertos: `pip` (`/backend`), `npm` (`/frontend/panel_admin`), `docker` (`/backend` y `/frontend/panel_admin`), `github-actions` (`/`).
  - AC-02: versiones minor y patch se agrupan en un solo PR por ecosistema; las majors llegan como PRs individuales.
  - AC-03: se ignoran las actualizaciones **major** de Django, `@angular/*`, `typescript`, y de las imágenes `python` y `node` (migraciones deliberadas); las de seguridad dentro de la serie siguen llegando.
  - AC-04: frecuencia semanal (lunes, `America/La_Paz`), `open-pull-requests-limit` acotado (5), etiqueta `dependencies` y prefijo de commit `chore(deps)`.
  - AC-05: el archivo valida contra el JSON Schema oficial de Dependabot (SchemaStore) y no modifica `deploy.yml` ni código de producto.
- **Edge/error cases:** si GitHub reporta error de configuración tras el merge (p. ej. `/backend` no detecta `requirements/`), se corrige en un task posterior; no bloquea.
- **Out of scope:** activar Dependabot alerts/security updates en los ajustes del repo (acción humana, se documenta), CI de tests en PRs, `pip-audit` en CI, auto-merge de PRs de Dependabot.

# Test Specification
- AC-01..AC-04: revisión del YAML y validación estructural (parseo con PyYAML).
- AC-05: validación con JSON Schema de SchemaStore (`dependabot-2.0`) y `git diff --name-only` limitado a `.github/dependabot.yml` + docs.
- **E2E: NO** — Dependabot solo se puede ejercitar en GitHub tras el merge a la rama por defecto; se verificará en Insights → Dependency graph → Dependabot.

# Implementation Plan
- **Files affected:** `.github/dependabot.yml` (nuevo). Backend/frontend: ninguno.
- **Steps:** 1) crear el archivo (AC-01..04); 2) validar contra el schema (AC-05); 3) documentar en el TASK el paso humano de activar alertas y security updates.
- **Risks / New dependencies:** ruido de PRs (mitigado); sin dependencias nuevas. Rollback: borrar el archivo.
