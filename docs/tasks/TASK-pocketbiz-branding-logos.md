# TASK-pocketbiz-branding-logos: Branding PocketBiz (logos, favicon, título y color principal)

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** SI
**Rama:** `task/TASK-pocketbiz-branding-logos`
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/9

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-12 19:26 | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-10-12 19:28 | INVESTIGATION → DESIGN → PLANNING | DDR propuesto; veredicto NEEDS_PLAN, sin arquitectura | delivery-design |
| 2026-10-12 19:40 | PLANNING → ENGINEERING | Specification READY (v1, modo COMPLETO); PR abierto | delivery-plan |

## Investigación

### Requerimiento
En `frontend/panel_admin/`:
1. Login: quitar el componente de imagen a la izquierda del formulario (no se usará por ahora).
2. Login: quitar el logo actual y colocar `main-logo.png`.
3. Menú lateral del usuario: quitar el logo actual y colocar `main-logo.png`; cuando el menú se contrae/achica, colocar `simple-logo.png`.
4. Pestaña del navegador: icono `pocketbiz.ico` y texto "PocketBiz".
5. Color principal de la aplicación: `#1677FF`.

Assets recibidos (adjuntos, aún no copiados al repo):
- `main-logo.png` = imagen 1 (adjunta como `1.webp`): logo horizontal "PocketBiz" + bolsillo + eslogan "tu negocio en el bolsillo", azul sobre fondo blanco, proporción aprox. 3:1 (~2000×650).
- `simple-logo.png` = imagen 2 (adjunta como `2.png`): solo el ícono del bolsillo, aprox. cuadrado (~1250×1250) con mucho margen blanco alrededor.
- `pocketbiz.ico` = `C:\Users\Lion\Downloads\pocketbiz-favicon.ico` (40 520 bytes; ICO con 6 tamaños, incluye 16×16 y 32×32 PNG).

### Hechos encontrados
- `frontend/panel_admin/src/app/authentication/signin/signin.component.html:5-7` — la columna izquierda `col-md-5` contiene solo `<img src="assets/images/login.jpg" class="login-card-img">`; el formulario está en `col-md-7` (línea 8).
- `signin.component.html:10-14` — logo del login: `<img src="assets/images/logo.png" class="logo">` + `<span class="logo-name">Oreva</span>` dentro de `.brand-wrapper`.
- `src/assets/scss/components/_auth.scss:1-7` — `.brand-wrapper .logo { height: 37px }`; `_auth.scss:34-39` define `.logo-name` (38px, bold) para `.login-body`.
- `src/app/layout/sidebar/sidebar.component.html:4-8` — marca del sidebar: `<img src="assets/images/logo.png" class="header-logo">` + `<span class="logo-name">Oreva</span>` dentro de `.sidebar-brand`.
- `src/assets/scss/layouts/_layout.scss:441-470` — `.sidebar-brand` alto 70px; `.header-logo { height: 30px }`; `.logo-name` 20px, mayúsculas con `letter-spacing: 3px`.
- `src/assets/scss/layouts/_sidebar.scss:1030-1032` — con `body.side-closed.submenu-closed` solo se oculta `.logo-name`; el `<img>` del logo no cambia.
- `src/app/layout/header/header.component.ts:144-156` y `:98-117` — la contracción se implementa con clases en `body`: `side-closed` + `submenu-closed` (toggle del botón y estado persistido en `localStorage['sidebar_status']`).
- `src/app/layout/sidebar/sidebar.component.ts:130-143` — al pasar el mouse sobre el sidebar contraído se quita `submenu-closed` y se agrega `side-closed-hover`; el sidebar se expande a 260px (`_sidebar.scss:1048-1051`) y vuelve al salir. Es decir, hay tres estados visuales: expandido, contraído (60px, `_sidebar.scss:978-981`) y contraído-con-hover (260px).
- `src/index.html:6` — `<title>Oreva - Angular 21+ Admin Dashboard Template </title>`; `src/index.html:9` — `<link rel="icon" href="assets/images/favicon.ico" type="image/x-icon">`. Existe `src/assets/images/favicon.ico` (el de la plantilla) y `src/assets/images/logo.png`.
- Color principal definido en varios sitios: `src/assets/scss/_variable.scss:4` (`primary: #6777ef`, mapa `$colors`, consumido vía `color(primary)` en 69 puntos), `src/assets/scss/skins/_white.scss:4` (`$color-primary: #6777ef`, skin `theme-white` activo por defecto: `src/app/config/config.service.ts:18`), y `#6777ef` / `#6777EF` / `rgb(103,119,239)` hardcodeados en 17 archivos: `_calendar.scss` (7), `_sidebar.scss` (7), `_settingSidebar.scss` (2), `_contact.scss` (2), `_button.scss` (2), `_lightsidebar.scss` (2), `_breadcrumb.scss`, `_card.scss`, `_form.scss`, `_layout.scss`, `_helpers.scss`, `_black.scss`, `_dark.scss`, `shared/styles/_table-actions.scss:17`, y `dashboard/dashboard2/dashboard2.component.ts` (3, colores de gráficos).
- Otros skins (`_cyan`, `_green`, `_orange`, `_purple` `#5864bd`, `_red`, `_black` `#252525`) definen su propio `$color-primary`; el usuario puede cambiarlos desde el right-sidebar (`right-sidebar.component.ts:53-66,104-111`, guarda `choose_skin` en `localStorage`).
- `src/app/authentication/signup/signup.component.html:12` también usa `logo.png` + "Oreva" (misma estructura que el login). `forgot`/`reset` no referencian logos (verificado con grep).
- `src/app/layout/header/header.component.html:153` — texto "Welcome to Oreva" en un dropdown de notificaciones (rastro de marca fuera del alcance explícito).
- Los textos del login (`Remember me`, `Sign in`, `Or Login With`, etc.) siguen en inglés/plantilla; no forman parte de este requerimiento.

### Hipótesis / supuestos no confirmados
- "Menú del usuario" se interpreta como el sidebar izquierdo (`app-sidebar`), que es donde está el logo de marca; el dropdown de usuario del header (`header.component.html:~170-182`) no contiene logo. Confirmar con el usuario si se refería a otra cosa.
- "Cuando se achica" se asume que cubre el estado contraído (`side-closed`); no está definido qué logo mostrar en el estado contraído-con-hover (el sidebar se ensancha a 260px): ¿`main-logo` o `simple-logo`?
- `#1677FF` se asume que reemplaza al primario del skin por defecto (`theme-white`); no está definido qué pasa con los otros skins seleccionables (¿se mantienen o se eliminan/unifican?) ni con los colores de gráficos.
- `main-logo.png` incluye el eslogan y fondo blanco opaco (no verificado si es transparente); en el sidebar de 70px de alto y 260px de ancho el eslogan podría quedar ilegible, y un fondo blanco puede verse mal en el skin de sidebar oscuro (`_darksidebar.scss`).
- `simple-logo.png` tiene margen blanco grande; podría requerir recorte para verse bien dentro de 60px.
- No se verificó el nombre/formato final de los archivos: el usuario los llama `main-logo.png`, `simple-logo.png`, `pocketbiz.ico`; los adjuntos llegaron como `1.webp`/`2.png` y `pocketbiz-favicon.ico`.
- No se verificó que el ICO funcione correctamente en todos los navegadores ni si hace falta `apple-touch-icon`/manifest (no existe uno hoy según el grep de `index.html`).

### Módulos y dependencias relacionadas
Solo frontend (`frontend/panel_admin/`): `authentication/signin` (y `signup` por compartir estructura), `layout/sidebar`, `layout/header` (lógica de contracción), `src/index.html`, SCSS de la plantilla (`assets/scss/_variable.scss`, `skins/*`, `layouts/*`, `override/*`, `components/*`) y `assets/images/`. El backend no se ve afectado.

### Implementaciones similares existentes
No hay un mecanismo de marca centralizado: logo y nombre están duplicados como `<img src="assets/images/logo.png">` + `<span class="logo-name">Oreva</span>` en signin, signup y sidebar. Para el color, el patrón de la plantilla es el mapa `$colors` en `_variable.scss` + `$color-primary` por skin, con numerosos valores hardcodeados.

### Comportamiento actual
Login: tarjeta de dos columnas, imagen decorativa a la izquierda y formulario con logo/"Oreva" a la derecha. Sidebar: logo 30px + texto "Oreva"; al contraerse solo desaparece el texto y queda el logo de la plantilla. Pestaña: título y favicon de la plantilla Oreva. Color primario: `#6777ef` (azul-violeta) en el skin por defecto.

### Restricciones
- `CLAUDE.md`: cambios acotados a un objetivo; avisar antes de instalar dependencias (no se necesita ninguna); frontend con tipos explícitos, sin `any`.
- La carpeta `frontend/panel_admin_doc/` es referencia y no se edita.
- Los assets deben copiarse al repo (`src/assets/images/`, cubierto por `angular.json` `assets: src/assets`); el ICO de Downloads está fuera del repo.

### Riesgos identificados
- Color hardcodeado en ~17 archivos: cambiar solo `_variable.scss`/`_white.scss` deja zonas en `#6777ef` (inconsistencia visual).
- Cambiar de logo según estado del sidebar involucra tres estados (expandido, contraído, contraído-hover) controlados por clases en `body`; riesgo de parpadeo o de mostrar el logo incorrecto en hover.
- `main-logo.png` con fondo blanco y eslogan pequeño dentro de 70px de alto; legibilidad y contraste con skins/sidebar oscuro.
- No hay tests del layout/sidebar que cubran el logo (solo `sidebar-menu.spec.ts`), por lo que la verificación sería visual.
- Los textos "Oreva" restantes (`header.component.html:153`, `typography.component.html:121`) quedarían con la marca antigua si no se incluyen en el alcance.

### Veredicto de complejidad
**NEEDS_PLAN** — Cambio acotado al frontend, sin cambio de contrato de API, modelos ni autorización; no requiere decisión arquitectónica, pero toca varios archivos de plantilla/estilos (login, sidebar, index.html, SCSS de color en ~17 archivos), por lo que excede un TRIVIAL_FIX.

### Diseño requerido
**SI** — Cambia superficie de UI visible en todas las pantallas (marca, color primario) y hay decisiones visuales abiertas: tamaño/encaje de los logos en login y sidebar, qué logo usar en el estado contraído-hover, tratamiento del layout del login sin la imagen izquierda (tarjeta centrada de una sola columna), y alcance del nuevo color frente a los skins existentes.

## Diseño
- [DDR-pocketbiz-branding-logos-marca-y-color](../design/DDR-pocketbiz-branding-logos-marca-y-color.md) — Propuesto. Login de una columna centrada con `main-logo`; sidebar con `main-logo`/`simple-logo` alternados por clases de `body`; título y favicon PocketBiz; primario `#1677FF` como fuente única en skin por defecto. Supuestos a confirmar: logo principal en contraído-con-hover, skins alternativos intactos, logo también en signup, fondo blanco del brand en sidebar oscuro.

## Arquitectura
_No aplica según veredicto_

## Plan
- [PLAN-2026-10-12-pocketbiz-branding-logos](../plans/PLAN-2026-10-12-pocketbiz-branding-logos.md) — **v1**, Modo COMPLETO, Specification readiness: **READY**. 8 AC (AC-01..AC-08); E2E: NO.

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
