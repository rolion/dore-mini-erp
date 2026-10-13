# PLAN-2026-10-13-perfil-usuario-menus-lateral-superior (v1)

**Task:** TASK-perfil-usuario-menus-lateral-superior · **Modo:** COMPACTO · **Specification readiness:** READY
**DDRs:** [DDR-perfil-usuario-menus-lateral-superior-avatar-iniciales](../design/DDR-perfil-usuario-menus-lateral-superior-avatar-iniciales.md) · **ADRs:** Ninguno

**Por qué COMPACTO:** solo frontend, sin cambio de API, modelo, permisos ni fronteras entre módulos; los datos ya están en la sesión. La regla de iniciales es simple, local y se expresa con pocos AC. El DDR es un ajuste de UI en dos barras, sin pantallas nuevas.

## Objective
Mostrar quién está conectado con un avatar de iniciales en el sidebar y en el header, con nombre y apellido y nombre de la empresa en el sidebar, y limpiar el header (sin buscador, mensajes ni notificaciones; menú de usuario solo con nombre, empresa y Logout).

# Specification

- **Expected behavior:**
  - Sidebar: en lugar de imagen, un avatar con las iniciales de la persona; debajo, nombre y apellido (respaldo `username`); debajo, el nombre de la empresa en el lugar del cargo.
  - Header: sin buscador, sin botón de mensajes y sin botón de notificaciones; el botón de usuario muestra el mismo avatar de iniciales; su menú tiene solo nombre y apellido, empresa y Logout.
  - Se conservan toggle del menú lateral, pantalla completa e idioma.
- **Acceptance criteria:**
  - AC-01: Iniciales = primera letra del primer nombre + primera del primer apellido, en mayúsculas ("María Quispe" → "MQ"); con solo uno de los dos, una letra; sin ninguno, primera letra del `username`; sin nada, "?".
  - AC-02: El sidebar muestra el avatar con esas iniciales (sin `<img>` de usuario), el nombre y apellido de la sesión y el nombre de la empresa; no aparece "Emily Smith" ni el cargo.
  - AC-03: Sesión sin empresa (guardada antes del aislamiento): el sidebar y el menú del header no muestran línea de empresa (ni vacía).
  - AC-04: El header no contiene el buscador (`.search-element`), ni los desplegables de mensajes ni de notificaciones.
  - AC-05: El botón de usuario del header muestra el avatar de iniciales (sin `<img>`).
  - AC-06: Al abrir el menú del botón de usuario solo hay: nombre (`.dropdown-title`), empresa (`.company-name`, si existe), separador y Logout; ya no están Profile, Email ni Settings. Logout sigue cerrando la sesión.
  - AC-07: El avatar es accesible: `role="img"` y `aria-label` con el nombre completo.
- **Edge/error cases:** sesión sin `firstName`/`lastName` (usa `username`, ver spec existente EDGE-03 del header); sesión nula (avatar con "?" y textos vacíos, sin errores); nombre o empresa largos (elipsis con `title`, sin desbordar); sidebar colapsado (solo avatar, 35px) y tema oscuro (texto legible).
- **Out of scope:** guardar fotos de perfil, gestionar cargos, backend, páginas `extra-pages/profile` y `email/inbox` (siguen accesibles por URL), i18n del texto "Logout", limpieza de estilos huérfanos de `.search-element` en SCSS ajenos al header (puede quedar).

# Test Specification

| AC | Verificación | Nivel |
|---|---|---|
| AC-01 | Casos de `userInitials` (nombre+apellido, solo nombre, solo `username`, vacío, minúsculas/espacios sobrantes, acentos) | Unit |
| AC-02, AC-03 | `sidebar.component.spec.ts` con `AuthService` simulado (con y sin empresa); sin `img` de usuario ni "Emily" | Unit (TestBed) |
| AC-04, AC-05, AC-06 | `header.component.spec.ts`: sin `.search-element`, sin `i-feather[name=mail|bell]`; avatar con iniciales; ítems del menú = nombre, empresa, logout; clic en Logout llama `logout()` | Unit (TestBed) |
| AC-07 | `user-avatar.component.spec.ts` (`role`, `aria-label`, `data-initial`) | Unit |

- **Regresión:** specs actuales de AC-15/EDGE-03 del header (nombre y empresa, respaldo a `username`) siguen verdes; logos del sidebar y `linkActiveOptions` sin cambios; `npm run lint` y `npm run build` sin errores por imports sin uso.
- **E2E: NO** — cambio de presentación sin flujo nuevo ni integración backend; los specs de componente cubren los AC. Se hace una verificación visual manual (sidebar expandido/colapsado, tema oscuro, móvil).

# Implementation Plan

- **Files affected (solo `frontend/panel_admin/`):**
  - Nuevo `src/app/shared/models/user-profile.ts` (+ spec): funciones puras `userFullName(user)` y `userInitials(user)` sobre `User | null`.
  - Nuevo `src/app/shared/components/user-avatar/user-avatar.component.{ts,html,spec.ts}`: componente standalone `app-user-avatar`, inputs `initials`, `label`, `size` (`'sm' | 'xl'`); renderiza `<figure class="avatar avatar-{size}" [attr.data-initial]="initials" role="img" [attr.aria-label]="label">`.
  - `src/app/layout/header/header.component.{html,ts,spec.ts}`: quitar buscador, mensajes, notificaciones, enlaces Profile/Email/Settings; avatar en el botón; `userDisplayName` usa `userFullName`; añadir getter `userInitials`; podar imports sin uso (`NgScrollbar`, `FormsModule`, `RouterLink`, `TranslateModule` si ya no se usan).
  - `src/app/layout/sidebar/sidebar.component.{html,ts,spec.ts}`: bloque de usuario con avatar, nombre y empresa; eliminar las propiedades sin uso `userFullName`/`userImg`/`userType`; getters basados en `AuthService.currentUserValue`.
  - SCSS: `src/assets/scss/layouts/_sidebar.scss` (tamaño 35px del avatar colapsado, elipsis de la línea de empresa, color de la empresa igual al del cargo en tema oscuro `skins/_darksidebar.scss`) y `src/assets/scss/override/_navbar.scss` (`.nav-link-user .avatar`, quitar regla de `img`).
  - `src/assets/i18n/{en,es,de}.json`: quitar `MENUITEMS.USER.POST` y `HEADER.SEARCH.TEXT` (quedan sin uso).
- **Steps:**
  1. Funciones `userFullName`/`userInitials` y sus tests (AC-01).
  2. Componente `app-user-avatar` y su spec (AC-07).
  3. Sidebar: usar avatar + nombre + empresa; ajustar SCSS (colapsado, elipsis, tema oscuro); actualizar spec con `AuthService` simulado (AC-02, AC-03).
  4. Header: eliminar buscador, mensajes y notificaciones; avatar en el botón; menú reducido; actualizar spec (AC-04, AC-05, AC-06).
  5. Limpiar imports, claves i18n huérfanas y estilos del botón de usuario.
  6. `npm run lint`, `npm test`, `npm run build` y revisión visual en navegador.
- **Risks:**
  - El avatar usa el color primario y la barra superior puede tener un fondo similar según el tema (`_navbar.scss`): verificar contraste en los temas y, si hace falta, ajustar con borde o fondo claro solo en `.nav-link-user .avatar`.
  - El avatar del sidebar colapsado vive dentro de reglas de la plantilla (`.user-panel .image`, `_sidebar.scss:1036-1040`): el ajuste de tamaño debe quedar acotado al bloque de usuario.
  - El spec del sidebar hoy usa el `AuthService` real; al simularlo hay que dejar `getRouteInfo()` atendido por `HttpClientTesting`.
- **New dependencies:** ninguna.
