# PLAN-2026-11-23-actualizar-angular-vulnerabilidades (v1)

**Task:** TASK-actualizar-angular-vulnerabilidades · **Modo:** COMPACTO · **Specification readiness:** READY
**DDRs / ADRs:** Ninguno

## Objective
Dejar el frontend con Angular en la última versión de patch de la rama 21.x y con `npm audit` en cero avisos, sin cambios de comportamiento ni de código de producto.

# Specification
- **Expected behavior:** el frontend se comporta exactamente igual; el manifiesto exige un mínimo de Angular 21.x sin avisos conocidos y el lockfile resuelve versiones sin avisos.
- **Acceptance criteria:**
  - AC-01: `@angular/{animations,common,compiler,core,forms,localize,platform-browser,platform-browser-dynamic,router}` y `@angular/compiler-cli` con mínimo `^21.2.26`; `@angular/build` y `@angular/cli` con mínimo en la última 21.2.x; todos resueltos en `package-lock.json` a esas versiones y de la misma versión entre sí.
  - AC-02: `npm audit` en `frontend/panel_admin/` reporta 0 vulnerabilidades (cubre `hono` / `@hono/node-server`).
  - AC-03: `npm run build -- --configuration production`, `npm test` (Karma, headless), `npm run lint`, `npm run i18n:check` y `npm run test:tooling` pasan igual que en `main`.
  - AC-04: no cambian `src/`, `overrides`, `tools/minimatch-compat` ni el Dockerfile.
- **Edge/error cases:** si algún bump rompe build o pruebas, se fija la versión más alta que pase y se documenta; no se hacen cambios de código de producto para acomodarlo (se vuelve al plan).
- **Out of scope:** salto a Angular 22; librerías de terceros sin avisos (ng-select, ngx-charts, etc.); imágenes base Docker y dependencias Python del backend (no hay detalle de las alertas de Digital Ocean para revisarlas); agregar `npm audit` a CI.

# Test Specification
- AC-01: inspección de `package.json` y `npm ls @angular/core @angular/common @angular/router @angular/compiler @angular/forms` (todas iguales).
- AC-02: `npm audit` → 0 vulnerabilidades.
- AC-03: ejecución de build de producción, Karma, lint, `i18n:check` y `test:tooling`; comparar con el resultado base en `main`.
- AC-04: `git diff --stat` solo muestra `package.json` y `package-lock.json`.
- **E2E: NO** — sin cambios funcionales; el build y la suite de componentes cubren la compatibilidad. Revisión visual rápida con `npm start` opcional.

# Implementation Plan
- **Files affected:** frontend: `frontend/panel_admin/package.json`, `frontend/panel_admin/package-lock.json`.
- **Steps:**
  1. Medir línea base en `main` (build, tests, lint) para comparar (AC-03).
  2. Subir los floors de Angular en `package.json` y actualizar el lockfile dentro de 21.x con `npm install --package-lock-only` o `npm update @angular/...` (mismo major, sin paquetes nuevos) (AC-01).
  3. `npm audit fix --package-lock-only` para `hono`/`@hono/node-server` (AC-02).
  4. `npm ci` limpio y correr build de producción, Karma, lint, `i18n:check`, `test:tooling` (AC-03).
  5. Confirmar el diff acotado (AC-04) y documentar resultados en el TASK.
- **Risks / New dependencies:** sin paquetes nuevos; solo patches de paquetes ya instalados (requiere `npm ci`/`npm update`, aviso al usuario). Riesgo bajo de regresión; mitigado con la verificación completa. Rollback: revertir el commit (solo manifiesto y lockfile). Nota: `.npmrc` tiene `legacy-peer-deps=true`.
