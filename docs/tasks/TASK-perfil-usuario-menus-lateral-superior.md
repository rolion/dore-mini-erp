# TASK-perfil-usuario-menus-lateral-superior: Perfil de usuario con iniciales y limpieza del menú superior

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** SI
**Rama:** task/TASK-perfil-usuario-menus-lateral-superior
**Pull Request:** _sin abrir todavía_

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-13 | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-10-13 | DESIGN → PLANNING | DDR de avatar con iniciales y menú de usuario simplificado; veredicto NEEDS_PLAN | delivery-design |
| 2026-10-13 | PLANNING → ENGINEERING | PLAN v1 (COMPACTO) READY, PR abierto para aprobación humana | delivery-plan |

## Investigación

### Requerimiento
Menú lateral (sidebar):
1. La imagen/avatar del usuario no debe ser una imagen (no se guardan fotos): debe mostrar las iniciales del usuario (el usuario cree que ya existe un componente para esto).
2. Debajo, en lugar del fijo "Emilia Smith", mostrar nombre y apellido del usuario.
3. Debajo, en lugar del cargo (no se gestionan cargos), mostrar el nombre de la empresa.

Menú superior (header):
4. Quitar el componente de búsqueda.
5. Quitar el botón de mensajes (icono sobre/envelope).
6. Quitar el botón de notificaciones (icono campana).
7. El botón de usuario (hoy con imagen pequeña) debe mostrar un avatar con las iniciales, igual que en el sidebar.
8. Al hacer click en ese botón, el menú solo debe mostrar nombre de usuario, nombre de la empresa y el botón de logout.

### Hechos encontrados
- `frontend/panel_admin/src/app/layout/sidebar/sidebar.component.html:13-23` — bloque `li.sidebar-user-panel`: `<img src="assets/images/user.png" class="img-circle user-img-circle">`, nombre **hardcodeado** `Emily Smith` (línea 21) y cargo con `{{'MENUITEMS.USER.POST' | translate}}` (línea 22).
- `frontend/panel_admin/src/assets/i18n/es.json:8-10` (y `en.json`, `de.json`, mismas líneas) — `MENUITEMS.USER.POST` = "Gerente" en es; es la única referencia a esa clave (`sidebar.component.html:22`).
- `frontend/panel_admin/src/app/layout/sidebar/sidebar.component.ts:57-59` — declara `userFullName?`, `userImg?`, `userType?` que no se asignan ni usan en ningún lugar; el componente ya inyecta `AuthService` (`:70`) pero solo lo usa para decidir si carga el menú (`:112`).
- `frontend/panel_admin/src/app/layout/header/header.component.html:6-22` — `<form class="search-element">` con input y botón de búsqueda dentro del primer `<ul class="navbar-nav">`, junto al toggle del menú (líneas 3-8). El input no tiene lógica asociada (sin binding ni handler); usa la clave i18n `HEADER.SEARCH.TEXT` (`:12`; `assets/i18n/*.json:2-6`).
- `header.component.html:55-... ` — `<li>` del botón de mensajes (`<i-feather name="mail">`, con lista estática de mensajes de ejemplo con imágenes `assets/images/users/user-*.png`) y a continuación `<li>` de notificaciones (`<i-feather name="bell">`, datos estáticos de ejemplo). Ambos son contenido de plantilla sin datos reales.
- `header.component.html` (último `<li ngbDropdown>`) — botón de usuario: `<img src="assets/images/user.png" class="user-img-radious-style">`; menú con `dropdown-title` = `{{ userDisplayName }}`, `company-name` = `{{ companyName }}` (condicional) y además enlaces "Profile" (`/extra-pages/profile`), "Email" (`/email/inbox`), "Settings" (`href=""` sin acción) y "Logout" (`(click)="logout()"`).
- `frontend/panel_admin/src/app/layout/header/header.component.ts:174-183` — ya existen `userDisplayName` (nombre + apellido, con fallback a `username`) y `companyName` (`currentUserValue?.company?.name`), leyendo `AuthService.currentUserValue`; `logout()` en `:185`. Los imports `NgScrollbar`, `RouterLink`, `TranslateModule` solo se usan por la plantilla actual (ver Riesgos).
- `frontend/panel_admin/src/app/core/models/user.ts:6-15` — `User` tiene `firstName`, `lastName`, `username`, `company?: {id, name}`; no hay campo de imagen. `company` y `role` pueden faltar en sesiones guardadas antes del aislamiento por empresa (`:11`).
- `frontend/panel_admin/src/app/core/service/auth.service.ts:42-45` — `currentUserSubject` (BehaviorSubject) con `currentUser` observable y `currentUserValue`; la sesión se persiste en localStorage (`startSession`, `readStoredUser`).
- `frontend/panel_admin/src/assets/scss/components/_avatar.scss:4-16, 91-100` — la plantilla ya trae el estilo `.avatar` (tamaños `avatar-xs/sm/lg/xl`, `bg-*`) y `.avatar[data-initial]::before` que pinta `attr(data-initial)` centrado. Su única demostración es `avatar.component.html:103-107` (`<figure class="avatar ..." data-initial="UM">`).
- `frontend/panel_admin/src/app/advanced-component/avatar/avatar.component.ts:1-15` — `AvatarComponent` es solo la **página de demostración** de la plantilla (ruta en `advanced-component.routes.ts`), sin inputs ni lógica; **no es un componente reutilizable** de iniciales.
- Búsqueda de `initial`/`iniciales` en `src/app` y `assets/scss`: ninguna función ni componente propio calcula iniciales; solo existe el estilo CSS del paso anterior.
- `frontend/panel_admin/src/assets/scss/layouts/_sidebar.scss:885-945` — estilos `.sidebar-userpic-name`, `.profile-usertitle-job`, `.user-panel .image` (ancho 35%, máx 75px), `.user-img-circle`; variantes para sidebar colapsado (`:1024-1036`) y oscuro (`skins/_darksidebar.scss:129-131`). `.profile-usertitle-job` tiene `font-size: 11px; line-height: 10px`.
- `frontend/panel_admin/src/assets/scss/override/_navbar.scss:218-236` — `.nav-link-user img { width: 30px }` y `.user-img-radious-style` (borde 6px) dimensionan la imagen del botón de usuario; estilos de `.search-element` en `_navbar.scss:88, 312-318, 359, 509`, `rtl/_layout-rtl.scss:98`, `skins/_dark.scss:84`.
- `frontend/panel_admin/src/app/layout/header/header.component.spec.ts:36-60` — specs existentes del header cubren `.dropdown-title` (nombre) y `.company-name` (empresa) en el menú de usuario (AC-15 de `TASK-registro-usuarios-empresa-multitenant`). `sidebar.component.spec.ts` no provee un `AuthService` simulado (usa el real con `provideHttpClientTesting`) y solo prueba logos y `linkActiveOptions`.
- `docs/tasks/TASK-registro-usuarios-empresa-multitenant.md:172` — el header mostrando nombre y empresa fue entregado en esa task (AC-15, UI-04); esta tarea modifica ese mismo menú.

### Hipótesis / supuestos no confirmados
- Se asume que "iniciales" = primera letra del nombre + primera letra del apellido, con fallback a la inicial del `username` para sesiones sin nombre/apellido (el fallback de nombre ya existe en `userDisplayName`); la regla exacta no fue especificada.
- Se asume que "nombre de usuario" en el menú desplegable (punto 8) significa nombre y apellido (lo que hoy muestra `userDisplayName`) y no el `username` técnico; ambiguo en el pedido.
- Se asume que los enlaces Profile / Email / Settings del desplegable deben desaparecer (el pedido dice "solo" nombre, empresa y logout); no se verificó si algún flujo depende de `/extra-pages/profile`.
- Se asume que la lista estática de mensajes/notificaciones es solo plantilla y no hay otro consumidor; no se encontró lógica real asociada en `header.component.ts`.
- No se verificó visualmente el aspecto en sidebar colapsado, tema oscuro ni responsive (requiere ejecutar la app).
- No se confirmó si las rutas `extra-pages/profile` y `email/inbox` seguirán accesibles por otra vía una vez retirado el enlace.

### Módulos y dependencias relacionadas
- Solo frontend, `frontend/panel_admin/src/app/layout/` (`header`, `sidebar`) y SCSS asociado en `src/assets/scss/`. Sin cambios de backend ni de contrato de API: el nombre, apellido y empresa ya llegan en la sesión (`LoginResponse`, `user.ts:17-27`).
- Dependen de `AuthService` (`@core`) para los datos del usuario; el header y el sidebar leen la misma fuente.
- No toca módulos de negocio (`features/*`) ni bounded contexts del backend.

### Implementaciones similares existentes
- Header ya resuelve nombre + empresa con getters sobre `AuthService.currentUserValue` (`header.component.ts:174-183`); el sidebar no lo hace y tiene el texto fijo.
- Avatar con iniciales: solo como estilo de plantilla (`_avatar.scss:91`) y ejemplo en `avatar.component.html:103-107`; no hay componente propio reutilizable en `src/app`.

### Comportamiento actual
- Sidebar: siempre imagen `user.png`, "Emily Smith" y el cargo traducido ("Gerente" en es), sin importar quién inició sesión.
- Header: buscador visible (inerte), botones de mensajes y notificaciones con datos de ejemplo, botón de usuario con imagen `user.png`; el desplegable muestra nombre, empresa (si existe) y además Profile, Email, Settings y Logout.
- Ninguna parte del código lee imagen de usuario porque el modelo no la tiene.

### Restricciones
- `CLAUDE.md`: frontend por `src/app/features/<modulo>/` para lógica de negocio; lógica no visual en services inyectables, tipos explícitos (sin `any`), sin suscripciones colgadas; avisar antes de instalar dependencias (no se necesita ninguna); cambios acotados — antes de tocar varios archivos, proponer plan y esperar confirmación.
- Textos de i18n en `assets/i18n/{en,es,de}.json`; la clave `MENUITEMS.USER.POST` y `HEADER.SEARCH.TEXT` quedarían sin uso (decisión de limpieza es de planificación).
- Reglas existentes por cumplir: no regresionar AC-15/EDGE-03 de `TASK-registro-usuarios-empresa-multitenant` (nombre y empresa en header; fallback a `username` y empresa oculta en sesiones antiguas).

### Riesgos identificados
- Dos lugares (sidebar y header) necesitarán la misma lógica de nombre/iniciales/empresa; hoy está solo en el header (`header.component.ts:174-183`), con riesgo de duplicarla.
- Sesiones antiguas sin `company` o sin nombre/apellido (`user.ts:11`; spec `header.component.spec.ts:50-60`): hay que considerar nombre vacío (iniciales vacías) y empresa ausente.
- El estilo `.avatar[data-initial]` es del template; el avatar del sidebar usa estilos propios (`.user-panel .image`, `.user-img-circle`, versión colapsada/oscura), por lo que el cambio puede verse desalineado en sidebar colapsado o tema oscuro.
- Al quitar el contenido del header, quedan imports sin uso (`NgScrollbar`, posiblemente `RouterLink`, `TranslateModule`, `FormsModule`) y estilos CSS huérfanos (`.search-element` en varios SCSS); el lint (`npm run lint`) podría marcarlos.
- Los specs existentes del header/sidebar deberán ajustarse; el spec del sidebar no simula `AuthService`.
- Nombre muy largo o empresa larga en el sidebar (`.profile-usertitle-job` con `line-height: 10px`) puede desbordar o solaparse.

### Veredicto de complejidad
**NEEDS_PLAN** — Cambio acotado a dos componentes de layout del frontend, sin cambios de API, modelo ni autenticación; todos los datos ya están en la sesión. Requiere un plan porque toca varios archivos (header, sidebar, SCSS, i18n, specs) y define una regla de iniciales.

### Diseño requerido
**SI** — Cambia la superficie visual de la barra lateral y la barra superior (nuevo avatar de iniciales con colores/tamaños, desplegable simplificado, ajuste en colapsado/oscuro) y debe quedar consistente con la plantilla; conviene decidir el aspecto del avatar antes de planificar.

## Diseño
- [DDR-perfil-usuario-menus-lateral-superior-avatar-iniciales](../design/DDR-perfil-usuario-menus-lateral-superior-avatar-iniciales.md) — componente de avatar de iniciales reutilizable (sidebar `avatar-xl`, header `avatar-sm`), regla de iniciales, sidebar con nombre y empresa, header sin buscador/mensajes/notificaciones y menú de usuario solo con nombre, empresa y Logout.

## Arquitectura
_Pendiente / No aplica según veredicto_

## Plan
- [PLAN-2026-10-13-perfil-usuario-menus-lateral-superior](../plans/PLAN-2026-10-13-perfil-usuario-menus-lateral-superior.md) — v1 · Modo COMPACTO · Specification readiness: READY

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
