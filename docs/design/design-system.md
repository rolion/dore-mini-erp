# Sistema de diseño — PocketBiz

**Estado:** Propuesto (no aprobado)
**Fecha:** 2026-10-12
**Etapa:** `delivery-design-system`
**Fuente de verdad:** los tokens del repositorio (`frontend/panel_admin/src/assets/scss/`). Este documento los recoge y propone derivados claramente marcados; no modifica estilos de producción.

Etiquetas: **[Repo]** valor leído del código · **[Derivado]** valor propuesto, calculado o elegido aquí, no existe en el repo · **[Medido]** contraste calculado (fórmula WCAG 2.x).

---

## 1. Principios y decisiones previas conservadas
- Se conserva la plantilla Oreva (Bootstrap 5, ngx-datatable, ng-select) y la marca PocketBiz de `DDR-pocketbiz-branding-logos-marca-y-color.md`. No se cambia de biblioteca de UI.
- Primario `#1677FF` (decisión del usuario). No se declara ningún HEX oficial del logo: el logo es un azul cercano a `#0052FF`/`#0A55FF` según el DDR de branding y **no es el primario de la UI**.
- Tipografía Inter, ya instalada vía Google Fonts (`index.html`).
- Idioma de la interfaz: español.

## 2. Tokens de color

### 2.1 Light (por defecto: skin `theme-white`)

| Token | Valor | Origen | Uso | Notas de contraste [Medido] |
|---|---|---|---|---|
| `primary` | `#1677FF` | [Repo] `_variable.scss:4`, `_white.scss:4` | Botones, acentos, iconos activos, foco | Texto blanco sobre primario: **4,10:1** → AA solo para texto grande/negrita (≥18,66 px o 14 px bold); para texto pequeño en botón usar peso 500+ y ≥14 px solo como compromiso aceptado en el DDR de branding |
| `on-primary` | `#FFFFFF` | [Repo] (`color: #fff` en `.btn-primary`) | Texto/icono sobre primario | — |
| `primary-text` | `#0958D9` | [Derivado] | Enlaces y texto azul de cuerpo pequeño | Sobre blanco **6,16:1**; sobre `#F6F6F6` **5,70:1** (AA) |
| `primary-hover` | `#0958D9` | [Derivado] | Hover/active de botón primario | Blanco sobre él **6,16:1**. Sustituye al violeta residual `#4f5ece` (ver §9) |
| `primary-selected` | `#125AC4` | [Repo] decisión AC-10 (menú light) | Ítem activo del menú lateral | Blanco **6,39:1**; negro 3,29:1 (por eso el texto es blanco) |
| `background` | `#F6F6F6` | [Repo] `$colors.body` | Fondo de página | — |
| `surface` | `#FFFFFF` | [Repo] `card_base` | Cards, modales, navbar | — |
| `text` | `#000000` | [Repo] `$colors.font` | Texto principal | 19,43:1 sobre fondo |
| `text-muted` | `#6C757D` | [Repo] `$colors.secondary` | Texto secundario **solo sobre blanco** (`surface`) | Sobre blanco **4,69:1** (AA); sobre `background` `#F6F6F6` **4,34:1** ✗ (F-02, revisión visual 2026-10-13) |
| `text-muted-on-bg` | `#5F6870` | [Derivado] (corrección F-02) | Texto secundario sobre el fondo de página `#F6F6F6` (notas, subtítulos, pies de foto de 12–14 px) | Sobre `#F6F6F6` **5,25:1** ✓; sobre blanco **5,67:1** ✓. Puede usarse también sobre blanco |
| `text-muted-weak` | `#98A6AD` | [Repo] `$colors.muted` | Solo decorativo/deshabilitado | Sobre blanco **2,50:1**: **no usar para texto informativo** |
| `border` | `#CCD3D8` | [Derivado] ≈ `lighten(grey, 20%)` de `$colors.grey #868E96` (mixin `form-control`) | Separadores y bordes de card | Sobre blanco **1,51:1**: decorativo, no basta como único indicador de un campo |
| `border-control` | `#868E96` | [Repo] `$colors.grey` | Borde de inputs/selects | Sobre blanco **3,32:1** ✓ (≥3:1 para componentes UI); el fondo del campo ya diferencia el control |
| `success` | `#54CA68` | [Repo] | Fondos de badge/iconos | Texto blanco **2,09:1** ✗; texto negro **10,03:1** ✓ |
| `success-text` | `#1F7A3A` | [Derivado] (corrige F-04; antes `#2F8F46`) | Texto/iconos de éxito sobre blanco, `background` y fondo de badge `#E8F8EC` | Sobre blanco **5,38:1**, sobre `#F6F6F6` **4,98:1**, sobre `#E8F8EC` **4,89:1** ✓. El valor anterior `#2F8F46` medía 4,09:1 / 3,71:1 sobre su badge ✗ |
| `warning` | `#FFA426` | [Repo] | Fondos de badge/iconos | Texto negro **10,59:1** ✓; blanco **1,98:1** ✗ |
| `warning-text` | `#B45309` | [Derivado] | Texto de advertencia sobre blanco | **5,02:1** ✓ |
| `danger` | `#FC544B` | [Repo] | Fondos de badge, botón destructivo | Texto blanco **3,23:1** (solo texto grande) |
| `danger-text` | `#C62828` | [Derivado] | Mensajes de error sobre blanco | **5,62:1** ✓ |
| `info` | `#3ABAF4` | [Repo] | Iconos, badges informativos | Texto negro recomendado |
| `focus` | `#1677FF` con anillo 3 px al 35 % | [Derivado] | `:focus-visible` | Hoy la plantilla elimina el `box-shadow` de foco en `.btn` (`_button.scss`): **hay que restituir un foco visible** (ver §9) |

### 2.2 Dark (skin `dark` + `dark-sidebar`)

| Token | Valor | Origen | Notas [Medido] |
|---|---|---|---|
| `background` | `#0F111D` | [Repo] `_dark.scss` | — |
| `surface` | `#16192A` | [Repo] `$color-dark-primary` / `$color-dark` | — |
| `text` | `#FFFFFF` | [Derivado] (el repo usa `#96A2B4` para texto base y `#FFF` en títulos) | 17,40:1 sobre `surface` |
| `text-muted` | `#96A2B4` | [Repo] `$color-font` | **6,73:1** sobre `surface` |
| `primary` | `#1677FF` | [Repo] (igual en ambos modos) | Sobre `surface` **4,24:1**; sobre `background` **4,58:1** → para texto azul pequeño en dark usar `primary-text-dark` |
| `primary-text-dark` | `#4C9AFF` | [Derivado] | **6,11:1** sobre `surface` y **6,59:1** sobre `background` ✓ |
| `border` | `#979DA6` | [Repo] `%extend_stylegroup` | Solo bordes de grupos de formulario |
| `success`/`warning`/`danger` | iguales a light | [Repo] | Badges con texto negro (success, warning) |

Regla: **no depender solo del color** para estados; todo badge lleva texto y, cuando aplique, icono (`fa-truck`, `fa-coins` ya usados en Pedidos).

## 3. Tipografía

| Token | Valor | Origen |
|---|---|---|
| Familia | `"Inter", sans-serif` | [Repo] `_misc.scss:21`, `index.html:14` (pesos 400/500/600/700) |
| Licencia | SIL Open Font License 1.1 (Google Fonts) | Verificada: Inter es OFL en Google Fonts |
| Base | 14 px / 400 | [Repo] `_misc.scss` |
| Escala propuesta | 12 (caption) · 14 (body) · 16 (lead/section) · 20 (h3) · 24 (h2) · 32 (h1) · 44 (display, solo landing) | [Derivado]; 12, 14, 16 y 24 aparecen en el repo; 20 en `.logo-name` |
| Pesos | 400 cuerpo · 500 etiquetas y botones · 600 títulos de card · 700 cifras destacadas y h1 | [Derivado] sobre pesos disponibles |
| Interlineado | 1,5 cuerpo · 1,25 títulos | [Derivado] |
| Cifras | `font-variant-numeric: tabular-nums` en importes y tablas | [Derivado] |

Nota: la plantilla aún tiene `font-family: "Time new Romans"` en `_misc.scss:166` (regla heredada); ver §9.

## 4. Espaciado, radios, sombras, densidad

| Token | Valor | Origen |
|---|---|---|
| Escala de espacio | 4 · 8 · 12 · 16 · 20 · 24 · 32 · 48 | [Derivado] (compatible con Bootstrap) |
| Padding de card | 20 px 25 px | [Repo] `_card.scss` |
| Margen inferior de card | 30 px | [Repo] `card_base` |
| Radio de card | 10 px | [Repo] `card_base($border-radius: 10px)` |
| Radio de botones/inputs | Bootstrap por defecto; 3 px en variantes de la plantilla | [Repo] parcial |
| Radio propuesto para landing | 8 px (controles), 12 px (cards) | [Derivado] |
| Sombra de card | `0 .46875rem 2.1875rem rgba(90,97,105,.1)` + 3 capas más | [Repo] `card_base` |
| Altura de control | 42 px (inputs y botones de formulario) | [Repo] `_form.scss` (`height: 42px`) |
| Altura de textarea | 64 px | [Repo] |
| Altura del header de marca (sidebar) | 70 px | [Repo] `.sidebar-brand` |
| Densidad | Estándar de formularios; tablas compactas 14 px | [Repo]/[Derivado] |

### Breakpoints [Repo] (`_variable.scss`)
`xs 0` · `sm 576` · `md 768` · `lg 992` · `xl 1200`. Referencias de diseño: **1440** (desktop) y **390** (móvil) según el protocolo.

## 5. Componentes y estados

Todos con foco visible `:focus-visible` (anillo `focus`), objetivo táctil ≥ 44 × 44 px en móvil y navegación por teclado.

| Componente | Variantes | Estados requeridos |
|---|---|---|
| **Botón** | primary (relleno `primary`, texto `on-primary`) · secondary/outline (borde `primary`, texto `primary-text`) · ghost/enlace · danger | default · hover (`primary-hover`) · active · focus-visible · disabled (opacidad 0,6, sin interacción) · loading (spinner + texto, `aria-busy`) |
| **Input / textarea** | texto, email, password, número, fecha | default · focus (borde `primary`) · filled · disabled · error (borde `danger-text` + mensaje) · éxito opcional |
| **Etiqueta** | siempre visible sobre el campo (no placeholder como etiqueta) | requerido con `*` y texto accesible |
| **Select / ng-select** | simple, con búsqueda remota | default · abierto · sin resultados · cargando · error |
| **Tabla / datatable** | ngx-datatable (listas largas), tabla Bootstrap (listas cortas) | cargando · vacío con mensaje · error con "Reintentar" · fila hover · fila seleccionada |
| **Card** | estándar · estadística (`card-statistic-4`) | cargando (skeleton/spinner) · error por tarjeta |
| **Navegación** | sidebar (expandido 260 px, contraído 60 px, hover) · header · breadcrumb · (landing) barra superior con anclas | activo (`primary-selected`, texto blanco) · hover · foco |
| **Diálogo** | modal Bootstrap / `Swal` | título, cuerpo, acción primaria, cancelar; datos de usuario con `titleText` (no HTML) |
| **Badge** | éxito, advertencia, peligro, info, neutro | texto + icono; contraste según §2 |
| **Notificación** | toast (`ngx-toastr`), alerta inline (`alert`) | éxito · error · aviso · info; `role="alert"` para errores |
| **Acordeón (FAQ)** | landing | colapsado · abierto · foco; contenido accesible por teclado |

## 6. Componentes de la landing (derivados, no existen en el repo)
Reutilizan los mismos tokens; son los únicos componentes nuevos que requiere el brief:
- **Hero:** `h1` 44/32 px (desktop/móvil), subtítulo 16–18 px, CTA primario + enlace secundario, imagen de producto.
- **Tarjeta de beneficio:** icono, título 600, texto 14–16 px.
- **Pasos numerados (3):** número en círculo `primary`, texto.
- **Tarjetas de plan (Gratis / Pro):** selector mensual/anual, precio en 700, lista de límites; Pro **sin botón de compra** (ver ux-brief Q21).
- **FAQ (acordeón).**
- **Bloque CTA de cierre.**

## 7. Bloque para prompts de Stitch (copiar tal cual)

```
Design system PocketBiz (Spanish UI, product for small-business owners that tracks sales, collections and expenses):
- Primary #1677FF, on-primary #FFFFFF, primary hover/active #0958D9, link/text-blue #0958D9.
- Light mode: page background #F6F6F6, surface/cards #FFFFFF, text #000000, muted text #5F6870 (use #6C757D only on white cards), border #CCD3D8.
- Dark mode: page background #0F111D, surface #16192A, text #FFFFFF, muted text #96A2B4, primary stays #1677FF (use #4C9AFF for small blue text).
- Status: success #54CA68 (use dark text on it; success text #1F7A3A), warning #FFA426 (dark text on it; warning text #B45309), danger #FC544B (danger text #C62828), info #3ABAF4.
- Font: Inter only. Sizes 12/14/16/20/24/32, 44 for landing display. Weights 400 body, 500 labels and buttons, 600 card titles, 700 figures and h1. Tabular numerals for money.
- Shape: cards radius 12px, controls radius 8px, input and button height 42px, soft shadow rgba(90,97,105,0.10).
- Spacing scale 4/8/12/16/20/24/32/48; card padding 20x25.
- Focus: visible 3px ring of #1677FF at 35% on every interactive element. Never rely on color alone for status: always add text or an icon.
- Logo: use text wordmark "PocketBiz" with the tagline "tu negocio en el bolsillo"; do not invent a logo color other than #1677FF.
Constraints: Bootstrap-style admin layout (left sidebar 260px, top header), Spanish copy, Bolivian boliviano amounts written like the product does, "Bs 1200.00" with a dot decimal and no thousands separator, e.g. "Bs 28.00", fictitious and clearly-labelled example data only, no testimonials, no invented statistics, no stock photos of people. Desktop reference 1440px, mobile 390px.
```

## 8. Reglas de uso
1. El primario nunca es el único portador de significado.
2. Texto azul pequeño: `primary-text` (`#0958D9`), no `#1677FF`.
3. Texto sobre `success`/`warning`: negro. Sobre `danger`: solo grande o usar `danger-text` sobre fondo claro.
4. No usar `text-muted-weak` (`#98A6AD`) para información. Sobre el fondo de página `#F6F6F6` usar `text-muted-on-bg` (`#5F6870`), no `#6C757D` (4,34:1).
5. Un solo CTA primario por vista.
6. Importes: formato **real del producto**, `Bs 28.00` (punto decimal; confirmado en capturas del 2026-10-13), alineados a la derecha y en cifras tabulares. (Antes decía `Bs 1.200,00`; corregido.)
7. Sin datos reales de negocios; datos de ejemplo rotulados como tal.
8. Los skins alternativos (cyan, green, orange, purple, red, black) no forman parte del sistema de marca (DDR de branding).

## 9. Discrepancias detectadas en el repo (pendientes, no corregidas aquí)
| # | Hallazgo | Evidencia | Impacto |
|---|---|---|---|
| D1 | Quedan 6 usos del violeta `#4f5ece` como hover/active/focus de `.btn-primary` en el skin por defecto | `skins/_white.scss:43-81` | Al pasar el cursor por un botón primario, aparece un violeta de la plantilla anterior |
| D2 | `.btn` elimina el `box-shadow` de foco (`box-shadow: none !important`) sin sustituto | `override/_button.scss:10-25` | Foco de teclado poco o nada visible: incumple "foco visible" del protocolo |
| D3 | Texto blanco sobre `#1677FF` mide 4,10:1 (<4,5:1) | cálculo §2.1 | Aceptado en el DDR de branding para peso 500+; en botones pequeños queda en el límite |
| D4 | `text-muted-weak` `#98A6AD` (2,50:1) y `warning`/`success` con texto blanco fallan AA | cálculo §2.1 | Evitar en landing; revisar en el panel |
| D9 | **Corregida en este documento (F-02):** `#6C757D` sobre `#F6F6F6` mide 4,34:1 (el token del repo es válido solo sobre blanco, 4,69:1). En el panel actual `$colors.secondary` se usa sobre `body` `#F6F6F6` | `visual-review.md` F-02 | Documento: nuevo token derivado `text-muted-on-bg` `#5F6870`. **Código sin tocar**: revisar usos de `secondary` sobre fondo de página en una etapa de implementación |
| D10 | **Corregida en este documento (F-04):** `success-text` `#2F8F46` medía 4,09:1 sobre blanco y 3,71:1 sobre `#E8F8EC` | `visual-review.md` F-04 | Documento: `#1F7A3A` (4,89:1 sobre el badge). Pendiente: **F-03** (badge Pendiente de Stitch, `#CD6D00`) usar `warning-text` `#B45309` |
| D5 | `font-family: "Time new Romans"` (con errata) en una regla de `_misc.scss:166` | `layouts/_misc.scss:166` | Posible fuente incorrecta en un componente puntual; revisar |
| D6 | El menú light usa `#125AC4` solo como ítem activo; no existe token semántico para ello | DDR branding AC-10 | Se documenta como `primary-selected` |
| D7 | Valores derivados de este documento (`primary-text`, `*-text`, `primary-text-dark`, `border`) no existen como variables Sass | §2 | Hay que crear variables en una etapa de implementación; no se tocó producción |
| D8 | El borde actual de inputs deriva de un tono claro (`#CCD3D8`, 1,51:1) | `_mixin.scss:141-144` | Para cumplir 3:1 el borde de control debería ser `border-control` `#868E96` |

## 10. Referencia visual en Stitch
Proyecto `PocketBiz` (ID `10435969640252772563`). Pantalla "Componentes", desktop 1440, light, estado **propuesto**. IDs, exportación y limitaciones en `docs/design/screens.md`.

## 11. Desviaciones de la referencia respecto a los tokens
Revisión sobre la **miniatura 319×512** y sobre el texto devuelto por Stitch y el `designMd` del design system; no se pudo medir colores en píxeles.

| # | Desviación | Fuente | Acción sugerida |
|---|---|---|---|
| S1 | Stitch generó su propio design system "PocketBiz Operational Admin" con `namedColors.primary = #0057C2` y `surface/background = #F6FAFF`, aunque `customColor`/`overridePrimaryColor` = `#1677FF`. El `designMd` sí conserva `#1677FF` y `#F6F6F6` | `list_design_systems` | No usar `namedColors` de Stitch como tokens; los del repo prevalecen. Mantener el bloque de §7 en cada prompt |
| S2 | El `designMd` fija borde de inputs `#CCD3D8` (1,51:1) | `designMd` | Coincide con el repo hoy; para cumplir 3:1 usar `border-control` `#868E96` (D8) |
| S3 | La sombra de card es mucho más suave (`0 1px 3px rgba(0,0,0,.04)`) y con borde 1 px; el repo usa sombra grande sin borde | `designMd` | Decisión de diseño: se acepta para landing; el panel conserva el repo |
| S4 | Se añadió "Configuración" en el menú, columna "Acciones", indicador "+12 %" y "Insumos 84 % / Servicios 16 %" | texto de Stitch | Contenido inventado de ejemplo; no usar como dato del producto. La landing no debe mostrar cifras que parezcan reales |
| S5 | Cliente y montos ficticios y "formato venezolano" (`Bs 1.200,00`) | texto de Stitch | El formato es el esperado en este documento; los nombres son ejemplo |
| S6 | Variante dark no generada | — | Pendiente |
| S7 | Foco: se muestra aro de 3 px al 15 % en el `designMd` (token de este documento: 35 %) | `designMd` | Igualar a 35 % para visibilidad (≥3:1 con el fondo) |
| S8 | Contraste de los badges y textos pequeños de la miniatura no verificable | miniatura | Verificar en la pantalla final con herramienta |
