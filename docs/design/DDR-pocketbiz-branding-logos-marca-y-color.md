# DDR-pocketbiz-branding-logos-marca-y-color: Marca PocketBiz en login, sidebar, pestaña y color primario

**Estado:** Propuesto
**Task relacionado:** TASK-pocketbiz-branding-logos
**Fecha:** 2026-10-12

## Contexto
La app arrastra la marca de la plantilla Oreva: logo `logo.png` + texto "Oreva" (login, signup, sidebar), imagen decorativa `login.jpg` en el login, título/favicon de la plantilla y primario `#6777ef`. El requerimiento pide pasar a PocketBiz con `main-logo.png` (logo horizontal con eslogan), `simple-logo.png` (solo bolsillo), favicon `.ico`, título "PocketBiz" y primario `#1677FF`. La investigación dejó cuatro puntos abiertos (logo en hover del sidebar contraído, alcance del color sobre los skins, signup, sidebar oscuro); este DDR propone un valor por defecto para cada uno, marcados como **Supuesto** para que el usuario los confirme o corrija.

Hechos verificados sobre los assets (adjuntos de la sesión): ambos son PNG/WebP RGBA **con fondo transparente** (esquina `(0,0,0,0)`), ambos con margen transparente grande: `main-logo` 2000×667 con contenido ~1875×522 (≈3,6:1), `simple-logo` 1254×1254 con contenido ~1020×1000 (≈1:1). Color de marca azul sólido, cercano a `#0052FF`/`#0A55FF`, distinto del `#1677FF` pedido para la UI.

## Pantallas/flujos afectados
1. **Login** (`/authentication/signin`): la persona ve la marca y se autentica. Cambia: sin imagen lateral, logo principal.
2. **Sidebar** (todas las pantallas autenticadas): marca arriba del menú en sus tres estados (expandido, contraído, contraído con hover).
3. **Pestaña del navegador** (todas): título e icono.
4. **Color primario** (todas): botones, enlaces activos, ítem activo del menú, paginación, badges, switches, etc.
5. *(Supuesto, ver abajo)* **Signup**: solo el cambio de logo, por coherencia.

## Componentes/patrones elegidos

### Login
- Se reutiliza el componente existente `signin.component.html` y las clases de plantilla `.login-card` / `.login-body` / `.brand-wrapper` (`src/assets/scss/components/_auth.scss`); no se introduce un componente nuevo.
- Se elimina la columna de imagen (`col-md-5` + `login-card-img`) y el formulario pasa a ocupar la tarjeta completa. La tarjeta queda **centrada y angosta** (ancho máx. ≈ 480–520 px) en lugar de estirarse a todo el `container`; si no, el formulario de una columna quedaría desproporcionado en pantallas anchas.
- Logo: `main-logo.png` reemplaza `logo.png` + `<span class="logo-name">Oreva</span>`. Se elimina el texto "Oreva" porque el logo ya contiene el nombre; mantenerlo duplicaría la marca. Tamaño: ancho ≈ 240–280 px (≈ 70–78 px de alto), centrado, con `alt="PocketBiz"`. En móvil (≤422 px, ya con padding reducido en `_auth.scss:31`) se limita con `max-width: 100%`.
- No se tocan los textos del formulario (siguen siendo los de la plantilla/ya localizados parcialmente): fuera de alcance.

### Sidebar
- Se reutiliza `.sidebar-brand` (`sidebar.component.html:4-8`, alto 70 px, `_layout.scss:441`). Se renderizan **dos** imágenes dentro del mismo enlace al dashboard y se alterna cuál es visible con las clases que el layout ya pone en `body` (`side-closed` + `submenu-closed`, `header.component.ts:98-117,144-156`; hover: `sidebar.component.ts:130-143`), sin lógica TypeScript nueva:
  | Estado (clases en `body`) | Logo visible |
  |---|---|
  | Expandido | `main-logo.png` |
  | Contraído (`side-closed submenu-closed`, 60 px) | `simple-logo.png` |
  | Contraído con hover (`side-closed side-closed-hover`, 260 px) | `main-logo.png` (**Supuesto**: el sidebar ya muestra textos del menú y hay espacio, mostrar el ícono ahí desperdicia ancho y parpadea al entrar/salir el mouse) |
- Tamaños: `main-logo` con `max-height ≈ 44 px` y `max-width ≈ 200 px` (cabe en los 70 px del brand con aire); `simple-logo` ≈ 30–32 px de alto, centrado en los 60 px.
- Se elimina el `<span class="logo-name">Oreva</span>` y sus reglas dejan de ser necesarias.
- En móvil (`sidebar-gone`, sidebar overlay) se ve siempre el logo principal.

### Pestaña
- `index.html`: `<title>PocketBiz</title>` y `<link rel="icon" href="assets/images/pocketbiz.ico" type="image/x-icon">`. Se conserva el ICO multi-tamaño recibido (incluye 16 y 32 px); no se agrega manifest ni apple-touch-icon (no existen hoy, no se piden).
- El título es fijo para toda la app; no se agrega título dinámico por ruta (fuera de alcance).

### Color primario `#1677FF`
- **Fuente única**: el valor vive en `$colors.primary` (`_variable.scss:4`) y en `$color-primary` del skin por defecto `_white.scss:4`; los ~17 archivos con `#6777ef`/`rgb(103,119,239)` hardcodeado pasan a usar esas variables (o el mismo valor nuevo si el archivo no puede importarlas), de modo que no queden zonas violáceas. Los tonos derivados (hover/active) ya se calculan con `color_darken`/`color_lighten` y se ajustan solos.
- Alcance sobre skins (**Supuesto**): el cambio aplica al **skin por defecto (`theme-white`) y al mapa global**. Los otros skins del right-sidebar (cyan, green, orange, purple, red, black) **no se modifican**: siguen siendo temas opcionales que la persona elige conscientemente; la identidad por defecto de la app es la de PocketBiz.
- Colores de gráficos (`dashboard2.component.ts:104,213,245`): se actualizan al nuevo primario por consistencia si la ruta es alcanzable desde el menú; si es una pantalla demo no enlazada, se deja y se anota.
- Contraste: `#1677FF` sobre blanco da ≈ 3,9:1; cumple para texto grande/UI (≥3:1) pero queda justo para texto pequeño (4,5:1). Se acepta para enlaces y botones con texto blanco en peso 500+; no se usa para cuerpo de texto largo.

## Alternativas consideradas
- **Un solo `<img>` cambiando `src` por clase/TypeScript** vs. **dos `<img>` alternados por CSS** (elegida): la primera exige lógica en el componente y puede parpadear en hover; la segunda reutiliza las clases de `body` existentes y es declarativa. Costo: una imagen extra cargada (≈ pocos KB tras optimizar).
- **`simple-logo` también en contraído-con-hover**: más uniforme con el estado contraído, pero el sidebar ancho quedaría con un ícono diminuto en 260 px. Descartado.
- **Mantener el texto "Oreva"/"PocketBiz" junto al logo**: redundante, el logo ya incluye el nombre. Descartado.
- **Conservar la imagen del login en blanco/oculta con `d-none`** en vez de borrar markup: el usuario dijo "de momento no lo usaremos", pero dejar código muerto contradice las reglas del proyecto; se elimina la columna (el asset `login.jpg` puede quedarse en `assets/` y el usuario lo reactivará si lo quiere).
- **Sobrescribir el primario solo con una variable CSS al final de `styles.scss`**: rápido, pero la plantilla compila colores en Sass y con `!important` hardcodeados; produciría doble fuente de verdad. Descartado en favor de la fuente única.
- **Eliminar los skins para fijar la marca**: más coherente visualmente, pero es un cambio de producto no pedido. Se deja como decisión futura.

## Comportamiento por privilegio/estado
No depende de rol/privilegio. Solo varía por estado del layout (sidebar expandido/contraído/hover y viewport móvil) y por skin/tema oscuro:
- **Sidebar oscuro (`dark-sidebar`, `_darksidebar.scss:87`)**: *(actualizado por indicación del usuario)* el fondo del brand sigue al modo: `$color-dark` en dark y claro en light; el logo es transparente y se muestra sobre ambos. Contraste del azul sobre `$color-dark` aceptado; no se genera versión blanca del logo (no hay asset).
- **Tema dark general** (`variant: dark`): mismo tratamiento que el sidebar oscuro; el login no tiene fondo oscuro dedicado en la plantilla, se verifica visualmente.
- Nada de esto es seguridad; no hay nota pendiente para backend/arquitectura.

## Preparación de assets (condición del diseño)
- `main-logo.png`: recortar el margen transparente (≈ 1875×522), exportar a ~1000 px de ancho (suficiente para 2× en pantallas densas) y optimizar.
- `simple-logo.png`: recortar al contenido (≈ cuadrado), exportar a ~256 px.
- Convertir el WebP recibido a PNG, ya que el requerimiento nombra `main-logo.png`.
- Destinos: `frontend/panel_admin/src/assets/images/main-logo.png`, `simple-logo.png`, `pocketbiz.ico` (copiado de `C:\Users\Lion\Downloads\pocketbiz-favicon.ico`).

## Consecuencias
- Marca y color consistentes en login, sidebar y pestaña; menos duplicación de "logo + texto" y una sola fuente del color primario.
- Deuda visual aceptada: **signup** y los textos "Welcome to Oreva" (`header.component.html:153`) y de la página de typography quedan con marca antigua si no se incluyen. **Supuesto**: se incluye el cambio de logo en signup (mismo markup que login, un cambio mecánico, manteniendo su imagen lateral porque no se pidió quitarla); lo demás queda fuera.
- Los skins alternativos conservan sus propios colores, por lo que la persona puede apartarse de la paleta de marca desde el panel de configuración.
- `login.jpg`, `logo.png` y `favicon.ico` de la plantilla quedan sin uso; limpiarlos es opcional y no forma parte de la tarea.
- La verificación es visual (no hay tests de layout): la fase de plan debe incluir revisar los tres estados del sidebar, móvil y el skin de sidebar oscuro.
