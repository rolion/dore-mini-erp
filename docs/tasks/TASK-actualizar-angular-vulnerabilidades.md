# TASK-actualizar-angular-vulnerabilidades: Revisar y corregir vulnerabilidades de Angular en el frontend

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** NO
**Rama:** task/TASK-actualizar-angular-vulnerabilidades
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/116

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-23 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-11-23 | INVESTIGATION → PLANNING | Veredicto NEEDS_PLAN, sin diseño | delivery-start |
| 2026-11-23 | PLANNING → ENGINEERING | Plan v1 READY | delivery-start |
| 2026-11-23 | ENGINEERING → REVIEW | Implementación completa | delivery-build |
| 2026-11-23 | REVIEW → PUBLISH | Quality Gate PASS | delivery-publish |

## Investigación

### Requerimiento
Digital Ocean envía alertas de vulnerabilidades en varios lenguajes y frameworks. Se pide revisar si hay alguna vulnerabilidad para la versión de Angular del proyecto y corregirla sin introducir bugs en el frontend.

### Hechos encontrados
- `frontend/panel_admin/package.json:13-21` — Angular `^21.0.8` (animations, common, compiler, core, forms, localize, platform-browser(-dynamic), router); `@angular/cli ^21.2.29`, `@angular/build ^21.0.5`, `@angular/compiler-cli ^21.0.8`.
- `frontend/panel_admin/package-lock.json` — versiones instaladas: `@angular/core|common|compiler|router|forms|platform-browser` **21.2.25**; `@angular/cli` 21.2.29.
- Registro npm: última 21.x es **21.2.26** (tag `v21-lts`); `latest` es 22.3.0 (otro major).
- Avisos de seguridad publicados por Angular (`gh api repos/angular/angular/security-advisories`) que aplican a la rama 21.x y a paquetes que usamos (`core`, `common`, `compiler`, `router`): todos están corregidos en **≤ 21.2.25** (el más reciente, GHSA-57xq-rjx2-v5xh y GHSA-62vg-58rm-qff7 en router, corregidos en 21.2.25; GHSA-hh8m-fm6v-7cvg en core/compiler, 21.2.20; GHSA-jj27-h5hq-8x99 i18n, 21.2.19). La versión instalada ya los incluye.
- Único aviso de 21.2.26: GHSA-ffj9-42qx-f38h en `@angular/upgrade`, paquete que no usamos.
- Los avisos restantes son de `@angular/platform-server` / SSR, `@angular/service-worker` y `HttpTransferCache`/hidratación: el proyecto no usa SSR (`angular.json` solo tiene `@angular/build:dev-server`; ninguno de esos paquetes está en `package.json`; sin usos de `provideClientHydration`/`HttpTransferCache` en `src/`).
- `src/` no usa `bypassSecurityTrust*` ni `[innerHTML]` fuera de specs.
- `npm audit` (2026-11-23): **2 avisos moderate, 0 high/critical**, ambos transitivos y de desarrollo: `hono` 4.13.14 y `@hono/node-server` 2.1.5, traídos por `@angular/cli → @modelcontextprotocol/sdk`. No entran al bundle de producción ni al contenedor nginx final (Dockerfile multi-stage, solo se copia `dist/oreva/browser/`). `npm audit fix --package-lock-only` los resuelve (hono 4.13.21, node-server 2.1.11) cambiando solo `package-lock.json` (6 líneas).
- `frontend/panel_admin/package.json:90-96` — ya existen `overrides` y el adaptador `tools/minimatch-compat` por avisos anteriores (commit `63bd4a74`); no deben tocarse.
- `frontend/panel_admin/Dockerfile:1,27` — build en `node:22-alpine`, runtime `nginx:stable-alpine`.

### Hipótesis / supuestos no confirmados
- Las alertas de Digital Ocean probablemente combinan: los 2 avisos dev (`hono`), imágenes base Docker (`node`, `nginx`, `python`), y dependencias del backend Python. No tenemos acceso al detalle de las alertas; no se pudo confirmar cuál las originó.
- Los floors `^21.0.8` permiten que una instalación sin lockfile resuelva versiones anteriores a 21.2.20 (vulnerables); con `npm ci` no ocurre.

### Módulos y dependencias relacionadas
Solo `frontend/panel_admin/` (`package.json`, `package-lock.json`). Sin cambios de código, backend ni contratos.

### Implementaciones similares existentes
Commit `63bd4a74` («resolve title tests and npm advisories») resolvió avisos anteriores con `overrides` + verificación completa lint/build/Karma.

### Comportamiento actual
Build y bundle usan Angular 21.2.25 sin avisos aplicables.

### Restricciones
`CLAUDE.md`: avisar antes de instalar dependencias (aquí solo se suben patches de paquetes ya presentes, sin paquetes nuevos); no tocar `.env`; no editar `overrides`/`minimatch-compat` sin necesidad.

### Riesgos identificados
- Bump de patch dentro de 21.2.x: riesgo bajo, pero debe verificarse build de producción, Karma, lint, `i18n:check` y `test:tooling`.
- Subir a Angular 22 sería un salto de major con riesgo de regresión visual/funcional en la plantilla Oreva y sus librerías de terceros (varias con peer `^21`): fuera de alcance.
- El aviso `@angular/cli` 21.2.31 podría cambiar el árbol de dependencias de desarrollo; se valida con `npm audit`.

### Veredicto de complejidad
**NEEDS_PLAN** — cambio acotado de dependencias (manifiesto y lockfile), sin decisión arquitectónica, pero que requiere verificación completa para no introducir regresiones.

### Diseño requerido
**NO** — no hay cambios de pantallas ni de UI.

## Diseño
No aplica.

## Arquitectura
No aplica según veredicto.

## Plan
`docs/plans/PLAN-2026-11-23-actualizar-angular-vulnerabilidades.md` (v1, COMPACTO, READY).

## Implementación
- `frontend/panel_admin/package.json`: mínimos `^21.2.26` para animations, common, compiler, compiler-cli, core, forms, localize, platform-browser(-dynamic), router; `@angular/build` y `@angular/cli` `^21.2.31` (AC-01).
- `package-lock.json`: Angular 21.2.26, cli/build 21.2.31 (con `@angular-devkit/*`, `@schematics/angular`, vite/rollup en su patch), `hono` 4.13.21 y `@hono/node-server` 2.1.11 (AC-02: `npm audit` → 0 vulnerabilidades).
- Sin cambios en `src/`, `overrides`, `tools/minimatch-compat` ni Dockerfile (AC-04). Sin paquetes nuevos; `npm ci --ignore-scripts`.
- Verificación propia (no es el Quality Gate): `i18n:check`, `test:tooling` (4/4), `lint`, build de producción y Karma 1768/1768 pasan con Angular 21.2.26 (AC-03).
- Desviaciones: ninguna. Deuda: avisos peer de librerías de terceros (`^19/^20`) preexistentes por `legacy-peer-deps`; el build emite avisos CSS «Unmatched selector» de la plantilla, preexistentes.

## Review
**PASS** (subagente aislado, sin hallazgos). AC-01..AC-04 verificados: `npm ls` Angular 21.2.26 / cli-build 21.2.31; `npm audit` 0; build de producción OK; Karma 1768/1768; lint, `i18n:check` (2453 claves, 0 faltantes) y `test:tooling` 4/4; diff solo `package.json`, `package-lock.json` y docs. Nota: el lockfile *elimina* la entrada opcional `@napi-rs/lzma-linux-x64-gnu` (binario de plataforma que npm regenera según el SO); revisión visual no aplica (sin cambios de UI).

## Publicación
PR #116 listo para aprobación humana. Cambio de dependencias de frontend, sin impacto en auth/BD/infraestructura. No se mergea.
