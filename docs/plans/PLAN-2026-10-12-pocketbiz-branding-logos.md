# PLAN-2026-10-12-pocketbiz-branding-logos (v1)

**Task:** TASK-pocketbiz-branding-logos
**Modo:** COMPLETO (eje 3: DDR con impacto visual relevante — marca y color primario en toda la app)
**DDRs relacionados:** [DDR-pocketbiz-branding-logos-marca-y-color](../design/DDR-pocketbiz-branding-logos-marca-y-color.md)
**ADRs relacionados:** Ninguno
**Specification readiness:** READY

## Objective
Reemplazar la marca de la plantilla Oreva por PocketBiz en el panel Angular: logo y layout del login, logo del sidebar (con variante contraída), título y favicon de la pestaña, y color primario `#1677FF`.

## Context
Ver `TASK-pocketbiz-branding-logos` (Investigación) y el DDR. Vigencia verificada el 2026-10-12 con `HEAD == origin/main` (`ff16234`): las rutas y líneas citadas en la investigación siguen vigentes. Cambio solo de frontend, sin backend ni contrato de API.

# Specification

## Domain context
Sin bounded context de negocio: es presentación del panel (`frontend/panel_admin/`). No aplica DDD.

## Ubiquitous language
| Term | Meaning | Source |
|---|---|---|
| main-logo | Logo horizontal PocketBiz con eslogan ("tu negocio en el bolsillo"), PNG transparente | TASK / DDR |
| simple-logo | Solo el ícono del bolsillo, PNG transparente | TASK / DDR |
| Sidebar contraído | `body.side-closed.submenu-closed` (60 px) | `header.component.ts:98-117,144-156` |
| Contraído con hover | `body.side-closed.side-closed-hover` (260 px) | `sidebar.component.ts:130-143` |
| Primario | `$colors.primary` (`_variable.scss:4`) y `$color-primary` del skin `theme-white` (`_white.scss:4`) | código |

El usuario escribió "menú del usuario" y "se achica"; se interpretan como el sidebar izquierdo y su estado contraído (supuesto del DDR).

## Current behavior
Ver TASK → Hechos encontrados (login con imagen lateral y logo+"Oreva"; sidebar con `logo.png`+"Oreva"; título/favicon de la plantilla; primario `#6777ef`).

## Expected behavior
- El login es una tarjeta de una sola columna, centrada, sin imagen lateral y con `main-logo`.
- El sidebar muestra `main-logo` expandido y en contraído con hover, y `simple-logo` contraído; sin texto "Oreva".
- La pestaña muestra el título "PocketBiz" y el favicon de PocketBiz.
- Toda la UI con el skin por defecto usa `#1677FF` como primario; no quedan usos del `#6777ef` antiguo como color de marca.

## Acceptance criteria
- AC-01: El login ya no contiene la imagen `login.jpg` ni la columna `col-md-5`; el formulario ocupa la tarjeta completa, centrada y con ancho máximo ≈ 480–520 px.
- AC-02: El login muestra `assets/images/main-logo.png` con `alt="PocketBiz"` y no muestra el texto "Oreva" ni `logo.png`.
- AC-03: El sidebar contiene `main-logo.png` y `simple-logo.png`; con `body` expandido solo `main-logo` es visible.
- AC-04: Con `body.side-closed.submenu-closed` solo `simple-logo` es visible; con `side-closed-hover` vuelve a verse solo `main-logo`.
- AC-05: `index.html` declara `<title>PocketBiz</title>` y `<link rel="icon">` apuntando a `assets/images/pocketbiz.ico`.
- AC-06: `$colors.primary` y `$color-primary` de `_white.scss` valen `#1677FF`; ningún archivo de `src/` conserva `#6777ef`/`#6777EF`/`rgb(103,119,239)` salvo el color con nombre `indigo` de `_helpers.scss:7` (paleta genérica de colores de texto).
- AC-07: El logo en `signup` pasa a `main-logo` sin texto "Oreva" (la imagen lateral de signup se conserva).
- AC-08: Con `dark-sidebar` activo, el bloque `.sidebar-brand` tiene fondo blanco y el logo se distingue.

## Edge cases
- EDGE-01: Móvil (≤422 px): el logo del login no desborda (`max-width: 100%`).
- EDGE-02: En `sidebar-gone` (overlay móvil) se ve `main-logo`.
- EDGE-03: Al entrar/salir con el mouse en contraído, no debe mostrarse ambos logos a la vez ni parpadear de forma visible.
- EDGE-04: Otros skins del right-sidebar (cyan, green, orange, purple, red, black) conservan sus colores propios; no se modifican.

## UI behavior
Derivado del DDR (no se rediseña):
- UI-01: Login: `main-logo` ≈ 240–280 px de ancho, centrado sobre el formulario.
- UI-02: Sidebar: `main-logo` con `max-height ≈ 44px` / `max-width ≈ 200px`; `simple-logo` ≈ 30–32 px, centrado en 60 px.
- UI-03: Contraste: `#1677FF` se usa en botones/acentos con texto blanco o texto grande; no para cuerpo de texto largo.

## Non-functional requirements
- Peso: `main-logo.png` ≈ 1000 px de ancho y `simple-logo.png` ≈ 256 px, optimizados (cada uno idealmente < 100 KB).
- No se agregan dependencias.

## Out of scope
- Eliminar o reducir los skins alternativos; títulos dinámicos por ruta; manifest/apple-touch-icon.
- Cambiar textos de plantilla en inglés del login/signup ("Sign in", "Remember me", …).
- "Welcome to Oreva" (`header.component.html:153`) y `typography.component.html:121`.
- Limpiar assets sin uso (`login.jpg`, `logo.png`, `favicon.ico`).
- Backend.

## Open questions
Supuestos del DDR que no bloquean (se implementan con el valor propuesto; si el usuario discrepa se ajusta en una iteración): `main-logo` en contraído con hover; skins alternativos intactos; logo también en signup; fondo blanco del brand en sidebar oscuro.

# Test Specification

## Unit tests
- `signin.component.spec.ts` (Karma/TestBed, ya existente): no existe `img.login-card-img`; existe `img.logo` con `src` terminado en `main-logo.png` y `alt="PocketBiz"`; no hay `.logo-name` (AC-01, AC-02).
- `sidebar.component.spec.ts` (hoy solo "should create"): el DOM tiene una `img` con `main-logo.png` y otra con `simple-logo.png` dentro de `.sidebar-brand`, y no hay `.logo-name` (AC-03).

## Integration tests
No aplica (sin backend).

## E2E
**¿Corresponde E2E?** NO — es un cambio visual sin flujo de usuario nuevo; Playwright no está en `package.json` y no se justifica instalarlo.

## Regression tests
`npm test` completo (el spec de signin conserva sus casos de AC-08/AC-09 del flujo de login) y `npm run build` sin errores de Sass.

## Verificación visual / estática (no automatizable con Karma)
- `grep` de `6777ef` en `src/` → solo `_helpers.scss` (AC-06).
- Revisión en navegador con `npm start`: login (desktop y 375 px), sidebar expandido / contraído / hover, `dark-sidebar` desde el right-sidebar, pestaña con título e icono, un botón primario y el ítem activo del menú (AC-04, AC-05, AC-08, EDGE-01..03).

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | Angular unit test (signin) + revisión visual |
| AC-02 | Angular unit test (signin) |
| AC-03 | Angular unit test (sidebar) |
| AC-04 | Revisión visual (depende de CSS y clases de `body`) |
| AC-05 | Inspección de `index.html` + revisión visual de la pestaña |
| AC-06 | `grep` estático + `npm run build` + revisión visual |
| AC-07 | Revisión visual (signup) / `grep` de `logo.png` en `authentication/` |
| AC-08 | Revisión visual con skin oscuro |

# Implementation Plan

## Architecture considerations
Sin ADR. Respeta `CLAUDE.md` (frontend en `src/app/...`, sin `any`, sin dependencias nuevas). No hay lógica TypeScript nueva: la alternancia de logos usa las clases de `body` ya existentes.

## Proposed solution
Dos `<img>` en `.sidebar-brand` alternadas por CSS; login reducido a una columna dentro de `.login-card` con modificador de ancho; color como fuente única en `_variable.scss` + `_white.scss`, con los hardcodeados reemplazados por `variable.color(primary)` / `$color-primary` donde el archivo ya puede importarlas, o por el mismo valor `#1677FF` en archivos sin acceso a las variables.

## Files/components affected
- Frontend (assets): `src/assets/images/main-logo.png`, `simple-logo.png`, `pocketbiz.ico` (nuevos).
- Frontend (markup): `src/index.html`, `authentication/signin/signin.component.html`, `authentication/signup/signup.component.html`, `layout/sidebar/sidebar.component.html`.
- Frontend (estilos): `components/_auth.scss`, `layouts/_layout.scss`, `layouts/_sidebar.scss`, `skins/_darksidebar.scss`, y los archivos con `#6777ef` listados en el TASK/grep (`_variable.scss`, `skins/_white.scss`, `_black.scss`, `_dark.scss`, `_lightsidebar.scss`, `_calendar.scss`, `_contact.scss`, `_settingSidebar.scss`, `override/_button.scss`, `_breadcrumb.scss`, `_card.scss`, `_form.scss`, `shared/styles/_table-actions.scss`).
- Frontend (TS): `dashboard/dashboard2/dashboard2.component.ts` (3 colores de gráfico).
- Tests: `signin.component.spec.ts`, `sidebar.component.spec.ts`.

## Implementation steps
1. **Assets** (AC-02..05): recortar márgenes transparentes y exportar `main-logo.png` (~1000 px de ancho) y `simple-logo.png` (~256 px) desde las imágenes recibidas (`1.webp`, `2.png`); copiar `C:\Users\Lion\Downloads\pocketbiz-favicon.ico` como `src/assets/images/pocketbiz.ico`. Usar una herramienta local ya disponible (p. ej. PIL); no instalar nada.
2. **Pestaña** (AC-05): título y `<link rel="icon">` en `index.html`.
3. **Login** (AC-01, AC-02, UI-01, EDGE-01): quitar la columna `col-md-5`; reemplazar `logo.png` + `logo-name` por `main-logo.png`; envolver/limitar el ancho de la tarjeta con un modificador en `_auth.scss` (sin romper `signup`/`forgot` que comparten `.login-card`).
4. **Sidebar** (AC-03, AC-04, UI-02, EDGE-02, EDGE-03): dos `<img>` (`.header-logo-main`, `.header-logo-mini`) en `sidebar.component.html`; CSS en `_layout.scss`/`_sidebar.scss`: `.header-logo-mini { display: none }`; bajo `.side-closed.submenu-closed` se invierte; eliminar el `logo-name`.
5. **Sidebar oscuro** (AC-08): en `_darksidebar.scss`, fondo blanco para `.sidebar-brand`.
6. **Color** (AC-06, UI-03): cambiar `_variable.scss:4` y `_white.scss:4`; reemplazar los hardcodeados; ajustar los 3 colores de `dashboard2.component.ts`; ejecutar el `grep` hasta que solo quede `_helpers.scss:7`.
7. **Signup** (AC-07): reemplazar logo y quitar texto en `signup.component.html`.
8. **Tests**: añadir los casos de `signin.component.spec.ts` y `sidebar.component.spec.ts` (AC-01..03); `npm test`, `npm run lint`, `npm run build`.
9. **Revisión visual** con `npm start` según la Test Specification.

## Risks
- `signup.component.html` y `forgot` comparten `.login-card`: el modificador del login no debe afectarlos (mitigación: clase nueva solo en signin).
- Reglas con `!important` y hardcodeados en skins pueden dejar tonos viejos: el `grep` los detecta, pero los derivados con `color_lighten/darken` solo se ven en la revisión visual.
- Sin tests de layout reales, AC-04 y AC-08 dependen de verificación manual.
- Bajo contraste del `#1677FF` en texto pequeño sobre blanco (≈3,9:1): aceptado en el DDR.

## New dependencies
Ninguna.
