# DDR-landing-pocketbiz-rutas-landing-y-entradas: Landing pública en "/" y pantallas de entrada bajo "/pocketbiz"

**Estado:** Propuesto
**Task relacionado:** TASK-landing-pocketbiz-rutas
**Fecha:** 2026-10-13

## Contexto
PocketBiz hoy abre directamente en el login (`app.routes.ts:13` redirige `/` a `/authentication/signin`). El usuario decidió (Q7) que la raíz muestre una landing pública y que el producto viva bajo `/pocketbiz` (`/pocketbiz/login`, `/pocketbiz/signup`, `/pocketbiz/**`). Q13/Q21 se ignoran (la sección "Planes" es informativa) y Q4 sigue sin definir (sin enlaces legales ni de contacto).

El contenido, los textos y el diseño visual de la landing ya están decididos en artefactos previos que este DDR **no repite**: `docs/design/ux-brief.md` (§4–§7), `docs/design/specs/landing-pagina-principal.md`, `docs/design/design-system.md`, `docs/design/screens.md` (referencias de Stitch) y `docs/design/visual-review.md` (16 hallazgos). Este DDR decide **con qué piezas de la plantilla se construye** y **cómo se comportan las pantallas de entrada** con el nuevo esquema de rutas.

Hechos verificados para esta etapa:
- `layout/app-layout/auth-layout/auth-layout.component.html` es solo `<router-outlet>` con `[dir]`; no aporta cabecera, pie ni estilo. `main-layout` trae sidebar y header del panel (no sirve para una página pública).
- La plantilla ya usa `ngbAccordion` de `@ng-bootstrap/ng-bootstrap` 20.0.0 (`package.json:31`) en `extra-pages/faqs/faqs.component.html:21-40` y `ui/accordion/accordion.component.html`.
- Existe una página de precios de la plantilla (`extra-pages/pricing/pricing.component.html`, `pricingTable`) con precios en `$` y iconos Material, pensada como demo con breadcrumb del panel.
- Login y registro ya son tarjeta única centrada con el logo `main-logo.png` (`assets/scss/components/_auth.scss:1-45`, `.login-card--single`); sus textos están en español (signup) y mezclados con inglés (login).
- El panel usa Bootstrap 5.3 (`package.json:45`), tokens en `assets/scss/_variable.scss` y botones `.btn-primary` de la plantilla.

## Pantallas/flujos afectados
1. **Landing** (`/`): la persona entiende qué es PocketBiz y crea su cuenta. Pantalla **nueva**.
2. **Login** (`/pocketbiz/login`, antes `/authentication/signin`): sin rediseño; cambian enlaces y destino post-login.
3. **Registro** (`/pocketbiz/signup`, antes `/authentication/signup`): sin rediseño; cambian enlaces y destino post-registro.
4. **Entrada del producto** (`/pocketbiz` sin subruta): punto de entrada que decide a dónde enviar según la sesión.
5. **Páginas de error y de sesión expirada** (404, 500, 401): destinos de "volver".
6. **Landing con sesión activa**: variante del estado de la misma pantalla.

No se diseñan pantallas nuevas de gestión, ni pantalla de contratación de Pro (Q21 ignorada), ni páginas legales (Q4).

## Componentes/patrones elegidos

### 1. Landing
- **Estructura:** una página de feature nueva, `features/landing/pages/landing` (convención de `CLAUDE.md`: `features/<modulo>/{pages,components,services,models}`), con **cabecera, secciones y pie propios**. No reutiliza `main-layout` (trae sidebar/header del panel) ni depende de `auth-layout` (es solo un `router-outlet`); el decidir si necesita un contenedor de ruta propio es de arquitectura.
- **Grid y utilidades:** Bootstrap 5.3 (`container`, `row`, `col-*`, utilidades `d-flex`, `gap-*`), consistente con el panel; sin nuevas dependencias.
- **Cabecera fija:** barra propia con wordmark (`main-logo.png`/`simple-logo.png` en móvil), anclas, "Iniciar sesión" (enlace) y "Empezar gratis" (`.btn.btn-primary`). Menú móvil con colapso de Bootstrap vía `NgbCollapse` de `@ng-bootstrap/ng-bootstrap` (ya instalado).
- **Botones:** `.btn .btn-primary` y `.btn-outline-primary` de la plantilla; altura 42 px como los formularios (`assets/scss/override/_form.scss`, `height: 42px`).
- **Tarjetas:** `.card` de la plantilla con radio 12 px (token del sistema; el panel usa 10 px en `card_base`, `_mixin.scss:9`). Se acepta la diferencia de 2 px solo en la landing (ver Consecuencias).
- **Iconos:** Font Awesome (`fas fa-*`) y feather ya cargados en la plantilla; se reutilizan los de Pedidos (`fa-truck`, `fa-coins`) para estados de entrega y cobro. No se introducen sets nuevos.
- **Acordeón de preguntas:** `ngbAccordion` con `[closeOthers]="true"`, igual que `extra-pages/faqs`, **sin** el cuadro de búsqueda de esa página; primer ítem abierto.
- **Selector Mensual/Anual:** `btn-group` de Bootstrap con `aria-pressed`, el mismo patrón de atajos que ya usan Pedidos y Reportes (`DDR-gastos-reporting-mvp-dashboard-y-reportes`), con estado "Anual" seleccionado por defecto según la referencia vigente. No hay cálculo: solo cambia el precio mostrado.
- **Tarjetas de plan:** `.card` con lista de límites; la tarjeta Pro **no tiene botón de compra** y muestra la etiqueta atenuada "Pago disponible próximamente". No se usa `pricingTable` de la plantilla (ver alternativas).
- **Teléfono del hero:** marco **CSS puro** genérico (nuevo, pequeño) con el `<img>` de `dashboard-movil-403-positivo.png`. El PNG se copia a `src/assets/images/`; no se usa la recreación de Stitch.
- **Sección "Entrega y pago":** tarjetas numeradas (`.card`) con capturas recortadas o, en móvil, la recreación HTML de las tarjetas de estado con los mismos textos (Q25 del spec; decisión de recorte pendiente de implementación).
- **Idioma:** español fijo, sin `ngx-translate` (igual que login y registro, `DDR-registro-usuarios-empresa-multitenant-pantalla-registro`).
- **Datos:** contenido estático tipado en un archivo de constantes de la feature; sin llamadas a la API.
- **Tokens:** los del repositorio y los derivados del sistema de diseño (`design-system.md` §2), incluidos `text-muted-on-bg` `#5F6870` y `success-text` `#1F7A3A`. Primario `#1677FF`; el texto blanco de botones mide 4,10:1 (decisión F-01 pendiente: `#1677FF` o `#0958D9`).

### 2. Login y registro
- Se reutilizan `SigninComponent` y `SignupComponent` **sin rediseño visual**.
- Cambios de comportamiento/enlaces:
  - "Sign Up" (login) → `/pocketbiz/signup`; "Inicia sesión" (registro) → `/pocketbiz/login`.
  - Tras éxito, ambos van al panel (`/pocketbiz/dashboard/main`).
  - El **logo** de login y registro enlaza a `/` (la landing). Es un cambio nuevo y pequeño que cierra el ciclo landing → registro → volver.
  - `forgot` y `reset` (demos de la plantilla) siguen siendo parte de `/pocketbiz/**`; sin cambios de diseño.
- El texto mezclado inglés/español del login es deuda anotada en `DDR-registro-usuarios-empresa-multitenant-pantalla-registro` y queda **fuera** de esta tarea.

### 3. Entrada `/pocketbiz`
- Sin subruta, la persona **nunca ve una página en blanco ni un 404**: con sesión va al dashboard; sin sesión, al login. Es una decisión de UX; el mecanismo (redirect, guard) es de arquitectura.

### 4. Páginas de error y sesión expirada
- **401 / sesión expirada:** el destino es `/pocketbiz/login` (no la landing): la persona quería entrar al producto.
- **404 y 500** ("Back to Home" hoy apunta a `/authentication/signin`): el destino pasa a `/pocketbiz` (que resuelve según sesión). No se rediseñan.
- **URLs antiguas** (`/authentication/*`, `/dashboard/*`, `/sales/orders`, …): la expectativa de UX es que **no den 404** a quien tenga un marcador; si redirigen o no es decisión de arquitectura.

## Alternativas consideradas
- **Landing con `main-layout` + ocultar sidebar** vs. **cabecera y pie propios** (elegida). La primera reutiliza un contenedor pero arrastra header, sidebar, `page-loader` y estilos del panel que habría que apagar uno a uno; la segunda aísla la landing y evita que los cambios del panel la rompan.
- **`pricingTable` de la plantilla** vs. **tarjetas de plan con `.card`** (elegida). La plantilla ofrece precios en `$`, iconos Material y 4 columnas de demo; adaptarla costaría más que construir dos tarjetas con el sistema de diseño y quedaría inconsistente (colores propios).
- **`ngbAccordion`** vs. **`<details>`/CSS**. `ngbAccordion` ya existe en la plantilla, trae foco y `aria-expanded` resueltos y se prueba igual que el resto; `<details>` evitaría dependencia pero introduce un tercer patrón de acordeón. Se elige `ngbAccordion`.
- **Marco de teléfono como imagen** vs. **CSS puro**. Una imagen del teléfono con la captura incrustada fija el tamaño y no escala bien; el CSS permite escalar a 260–300 px y mantener la captura nítida. Se elige CSS.
- **Navegación por anclas con scroll** vs. **varias páginas**: una sola página (decisión previa del brief).
- **Mostrar siempre el CTA de registro** vs. **ocultarlo si `REGISTRATION_ENABLED=False`**. No existe un endpoint que informe el interruptor al cliente; se deja el CTA visible y el registro muestra el error de la API (comportamiento actual de `SignupComponent`). Si arquitectura expone el flag, la landing podría adaptarse.
- **El logo de login/registro enlaza a `/`** vs. **sin enlace**. El enlace da una salida clara hacia la landing con costo casi nulo.

## Comportamiento por privilegio/estado
No hay roles distintos (un solo rol `admin`; la landing es pública).
| Estado | Landing | Login/Registro |
|---|---|---|
| Anónimo | Página completa; CTA "Empezar gratis" → `/pocketbiz/signup`; "Iniciar sesión" → `/pocketbiz/login` | Formulario normal |
| Con sesión activa | Cabecera y CTA principal cambian a "Ir a mi panel" → `/pocketbiz/dashboard/main`; **sin redirección forzada** | Sin cambio respecto a hoy (la plantilla no redirige; deuda ya anotada) |
| Sesión expirada (401) | — | Destino `/pocketbiz/login` |
| Registro cerrado (`REGISTRATION_ENABLED=False`) | CTA visible (el cliente no lo conoce) | Error de la API en el formulario |

**Nota de seguridad:** todo lo anterior es UX. La barrera real es el servidor (`CompanyAdminPermission`, token). Que `/pocketbiz/**` exija sesión es una responsabilidad del guard **y** del backend; el frontend no es la única barrera. Requiere que arquitectura defina cómo se aplica esa exigencia con el nuevo esquema de rutas.

## Estados de la landing
Contenido estático: sin carga ni error de datos. Imágenes con dimensiones reservadas y `alt`; si falla una imagen, el texto alternativo mantiene la página usable. Menú móvil abierto/cerrado. FAQ con un ítem abierto. Toggle Mensual/Anual. Estado "sesión activa" descrito arriba.

## Accesibilidad y responsive (de la spec, resumidas)
Un único `h1`; foco visible; objetivos táctiles ≥ 44 px en móvil; contraste según `design-system.md` (texto pequeño con `text-muted-on-bg`); `prefers-reduced-motion` respetado en el scroll por anclas; sin desborde horizontal a 390 px; `scroll-margin-top` ≥ altura de la cabecera.

## Consecuencias
- **Más simple:** sin dependencias nuevas; el acordeón, los botones y los iconos son los de la plantilla; la landing queda aislada del panel.
- **Deuda visual aceptada:** radio de tarjeta 12 px en la landing frente a 10 px del panel; la landing y el panel comparten tokens pero no estructura.
- **Pantallas que cambian de enlace aunque no se rediseñen:** login, registro, 404, 500, header (logout), guard e interceptor, menú lateral (`routes.json`), y todas las features con enlaces absolutos; el recuento está en la investigación del task.
- **No resuelto aquí (arquitectura):** cómo se monta la app bajo `/pocketbiz` (prefijo en el router o `base href`), si la landing es parte de la misma app, redirecciones de URLs antiguas, fallback del servidor, y el mecanismo de `/pocketbiz` sin subruta.
- **Contenido sujeto a la spec:** la sección "Planes" describe límites que el producto no aplica (Q13 ignorada); si el producto cambia, la landing debe actualizarse.
- **Referencia visual:** las pantallas de Stitch siguen siendo propuestas con desviaciones abiertas (`visual-review.md` F-01…F-16, `screens.md`); en caso de conflicto prevalecen la spec y este DDR.
