# DDR-perfil-usuario-menus-lateral-superior-avatar-iniciales: Avatar con iniciales y menú de usuario simplificado

**Estado:** Propuesto
**Task relacionado:** TASK-perfil-usuario-menus-lateral-superior
**Fecha:** 2026-10-13

## Contexto
La investigación halló que el sidebar muestra una imagen fija (`user.png`), el nombre hardcodeado "Emily Smith" y un cargo traducido (`sidebar.component.html:13-23`), y que el header tiene un buscador inerte, desplegables de mensajes y notificaciones con datos de ejemplo, y un botón de usuario con imagen cuyo menú incluye Profile/Email/Settings además de nombre, empresa y Logout (`header.component.html`). No se guardan fotos de usuario (`user.ts:6-15`). La plantilla ya trae el estilo `.avatar[data-initial]` (`_avatar.scss:91-100`), pero no un componente reutilizable (`AvatarComponent` es solo la página de demo, `avatar.component.ts:1-15`).

## Pantallas/flujos afectados
- **Barra lateral (todas las pantallas autenticadas):** bloque de usuario al tope del menú. La persona solo lo lee; no hay acción.
- **Barra superior (todas las pantallas autenticadas):** quita buscador, mensajes y notificaciones; el botón de usuario abre un menú con nombre, empresa y Logout.

No se crean pantallas nuevas ni se toca `extra-pages/profile`.

## Componentes/patrones elegidos
1. **Avatar de iniciales**: un único componente de presentación reutilizable (el nombre y la ubicación concretos los define `delivery-plan`) que renderiza la clase de plantilla `.avatar` con `data-initial` (`_avatar.scss:91-100`, ejemplo en `avatar.component.html:103-107`). Se usa idéntico en sidebar y header para cumplir "igual que en el menú lateral". Recibe el nombre completo/iniciales ya resueltos; no accede a `AuthService` por sí mismo.
2. **Regla de iniciales (decisión de UX):** primera letra del primer nombre + primera letra del primer apellido, en mayúsculas ("María Quispe" → "MQ"). Si falta uno de los dos, una sola letra. Si no hay nombre ni apellido (sesión antigua, `user.ts:11`), la primera letra del `username` — mismo respaldo que ya usa `userDisplayName` (`header.component.ts:174-179`). Si tampoco hay, se muestra "?".
3. **Color:** fondo por defecto de `.avatar` (`variable.color(primary)`, texto claro, `_avatar.scss:4-9`), para heredar el color de marca definido en `DDR-pocketbiz-branding-logos-marca-y-color`. Sin colores por usuario (no aportan valor con una sola persona visible).
4. **Tamaños:** sidebar expandido `avatar-xl` (75px, coincide con el `max-width: 75px` de `.user-panel .image`, `_sidebar.scss:910-923`); sidebar colapsado 35px (ancho ya fijado en `_sidebar.scss:1036-1040`, un valor intermedio entre `avatar-sm` 30px y 45px por defecto, se resuelve con un ajuste de SCSS en el plan); header `avatar-sm` (30px, igual al ancho actual de `.nav-link-user img`, `_navbar.scss:223-225`).
5. **Sidebar, textos:** línea 1 = nombre y apellido (`userDisplayName`, con respaldo a `username`); línea 2 = nombre de la empresa en el lugar del cargo, con truncado por elipsis y `title` con el texto completo para nombres largos. Si no hay empresa (sesión antigua), la línea 2 no se muestra. La clave `MENUITEMS.USER.POST` deja de usarse.
6. **Header, botón de usuario:** el avatar de iniciales reemplaza la `<img>`; se conserva el toggle de `ngbDropdown`. Se conservan sin cambios el botón de pantalla completa, el selector de idioma y el toggle del menú lateral.
7. **Header, menú desplegable:** solo (a) nombre y apellido como título, (b) empresa en texto secundario (oculta si no hay), (c) separador y (d) "Logout" en estilo de peligro (el que ya tiene). Se reutilizan `dropdown-title`, `company-name` y el ítem de logout existentes, así los selectores de los specs actuales (AC-15) siguen válidos. Se eliminan Profile, Email y Settings.
8. **Accesibilidad:** el avatar lleva `role="img"` y `aria-label` con el nombre completo, ya que las iniciales por sí solas no son legibles para lectores de pantalla.

## Alternativas consideradas
- **Avatar con iniciales mediante `.avatar[data-initial]` de la plantilla (elegida):** cero dependencias nuevas, consistente con la plantilla, funciona en sidebar y header con tamaños ya definidos. Costo: un ajuste de SCSS para el tamaño colapsado.
- **Imagen generada (SVG/canvas o servicio externo tipo ui-avatars):** más flexible visualmente pero añade código o una llamada externa con datos del usuario; descartada por sobreingeniería y privacidad.
- **Mantener la imagen `user.png` genérica y solo cambiar el texto:** no cumple el pedido y deja el avatar idéntico para todas las personas.
- **Dejar Profile/Email/Settings en el menú:** el pedido dice "solo" nombre, empresa y logout; además Email y Settings no tienen funcionalidad real en este producto (Settings es `href=""`). Descartado.
- **Cabecera: ocultar buscador/mensajes/notificaciones con CSS en vez de eliminarlos:** deja código muerto y datos de ejemplo en el DOM; descartado.

## Comportamiento por privilegio/estado
No cambia por rol: todas las personas autenticadas ven el mismo bloque, con sus propios datos. Estados cubiertos:
- Sesión con nombre, apellido y empresa → caso normal.
- Sesión antigua sin nombre/apellido → se muestra `username` e inicial del `username`.
- Sesión sin empresa → se omite la línea de empresa en sidebar y menú.
- Sidebar colapsado: se ve solo el avatar (el nombre y la empresa se ocultan, como ya ocurre con nombre y cargo en `_sidebar.scss:1024-1030`).
- Tema oscuro: los colores de texto del nombre y la empresa siguen las reglas de `_darksidebar.scss:129-131`; la empresa debe heredar la regla del cargo.

No aplica control de privilegio. Esto es solo presentación de datos de la propia sesión; no requiere decisión de arquitectura ni verificación de servidor.

## Consecuencias
- Sidebar y header muestran siempre quién está conectado y de qué empresa, sin imágenes que gestionar.
- Desaparecen datos de ejemplo y controles inertes del header (menos confusión, menos DOM).
- Quedan rutas de plantilla (`/extra-pages/profile`, `/email/inbox`) accesibles por URL pero sin enlace en el menú; se acepta y no se limpian en esta tarea.
- Estilos huérfanos de `.search-element` y de `.user-img-radious-style` en varios SCSS pueden permanecer; limpiarlos es opcional y lo decide el plan.
- Si en el futuro se guardan fotos de perfil, el componente de avatar es el único lugar a extender (mostrar imagen y, si falta, iniciales).
- Las claves i18n `HEADER.SEARCH.TEXT` y `MENUITEMS.USER.POST` quedarían sin uso en `en/es/de.json`.
