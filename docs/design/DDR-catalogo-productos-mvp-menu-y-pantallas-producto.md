# DDR-catalogo-productos-mvp-menu-y-pantallas-producto: Menú reducido y pantallas de Producto (lista, formulario, detalle)

**Estado:** Propuesto
**Task relacionado:** TASK-catalogo-productos-mvp
**Fecha:** 2026-10-08

## Contexto
La investigación del task muestra que hoy el menú lateral sale de `frontend/panel_admin/src/assets/data/routes.json` (21 entradas de demo) y que no existe ninguna pantalla de productos ni la carpeta `src/app/features/`. El pedido es: dejar solo Dashboard, agregar Catálogo → Producto, y desde ahí listar en una tabla de la plantilla, agregar, editar y ver el detalle completo (REQ-CAT-001 a 005). `docs/architecture/ddd.md:1035-1046` ya propone `features/products/pages/{product-list,product-form}`. La plantilla no trae roles: el login es real pero no hay privilegios diferenciados (ver `TASK-frontend-login-backend`), así que no hay variación por rol que diseñar.

## Pantallas/flujos afectados
1. **Menú lateral** (`layout/sidebar`): solo "Dashboard" y "Catálogo ▸ Producto".
2. **Lista de productos** (`/catalog/products`): consultar activos e inactivos, buscar por nombre, filtrar por estado, ir a crear, ver, editar y activar/desactivar (REQ-CAT-004, 003).
3. **Formulario de producto** (`/catalog/products/new` y `/catalog/products/:id/edit`): crear y editar nombre, descripción, precio (REQ-CAT-001, 002).
4. **Detalle de producto** (`/catalog/products/:id`): solo lectura de todos los datos, con accesos a editar y activar/desactivar (REQ-CAT-005, 003).

No se diseñan pantallas de ventas, historial ni eliminación: el requerimiento no las pide y REQ-CAT-005 prohíbe mezclar ventas históricas en la entidad Catalog. Tampoco hay botón "eliminar": el requerimiento habla de desactivar para no perder historial.

## Componentes/patrones elegidos

**Menú**
- Mismo mecanismo de la plantilla: editar `routes.json` y `sidebar.metadata.ts` no cambia (`panel_admin_doc/sidebar-menu.html`: "solo routes.json"). Dos entradas de primer nivel:
  - *Dashboard*: ítem simple (`class: ""`, `path: "/dashboard/main"`, icono feather `monitor`), sin submenú; es la "página por defecto" ya usada tras el login. Dashboard 2 deja de aparecer en el menú.
  - *Catálogo*: ítem con `class: "menu-toggle"` y un submenú *Producto* → `/catalog/products` (icono feather `package`, disponible porque `app.config.ts` registra `allIcons`). Es el patrón "Home" actual (`routes.json`, entrada 2).
- Se elimina el encabezado de grupo "Principal" (solo había un grupo para un menú que desaparece). Las etiquetas pasan por `translate`, así que se agregan claves `MENUITEMS.DASHBOARD` y `MENUITEMS.CATALOG.{TEXT,LIST.PRODUCT}` en `en.json`, `es.json` y `de.json` (el idioma por defecto cae a `en`, `language.service.ts:23`).

**Lista** — `ngx-datatable class="material"` con cabecera tipo `advance-table` (`src/app/advance-table/advance-table.component.html:12-58`): título, buscador `table-search-area`, botón redondo "+" (`btn-primary rounded-button`) para crear. Columnas: Nombre, SKU (si arquitectura lo incluye), Precio, Estado, Acciones. Estado con `badge-outline col-green` (Activo) / `col-red` (Inactivo), igual que `advance-table.component.html:83-98`. Acciones con los botones de la plantilla `btn btn-tbl-edit` (editar) más un botón de ver detalle y un botón de activar/desactivar; confirmación con `sweetalert2` y avisos con `ngx-toastr`, como en `advance-table.component.ts:98`. Se agrega un `<select class="form-select">` de estado (Todos / Activos / Inactivos) junto al buscador.

**Formulario** — página con el layout de `forms/form-validation/form-validation.component.html:1-50` (`main-content` → breadcrumb → `card`), campos `form-control`, etiquetas con `*` rojo y mensajes `small.form-text.text-danger` bajo el campo cuando es inválido y fue tocado. Campos: Nombre (obligatorio), Descripción (`textarea`), Precio de venta (`input type="number"` con `min=0`, `step=0.01`, obligatorio). En alta no hay campo de estado (nace activo, REQ-CAT-001); en edición tampoco: el estado solo cambia con activar/desactivar.

**Detalle** — misma estructura `card` del formulario con lista de datos de solo lectura (nombre, descripción, SKU si aplica, precio, estado en badge, fechas de creación/actualización) y botones "Editar", "Activar/Desactivar" y "Volver".

## Alternativas consideradas
- **Alta/edición en modal (patrón `advance-table`) vs. página propia.** El modal reutiliza el patrón exacto de la plantilla y es rápido, pero no tiene URL (no se puede abrir un producto por enlace), el detalle y la edición compartirían un modal sobrecargado y el HTML de ejemplo trae formularios no tipados y de ~100 líneas por modal que habría que reescribir de todos modos. Página propia: costo similar, URL navegable por producto (útil para el detalle completo pedido) y coincide con `product-form` de `ddd.md:1038-1041`. **Se elige página.**
- **Detalle como fila expandible (`data-tables/row-details`) vs. página.** La fila expandible evita navegar pero no alcanza para "detalle completo" ni para enlazar; se descarta.
- **`ngx-datatable` vs. tabla Bootstrap simple (`panel_admin_doc/bootstrap-table.html`).** La tabla Bootstrap es más simple pero no trae ordenamiento ni paginación y rompería la consistencia con las tablas ya presentes; se mantiene `ngx-datatable`, que es lo que el usuario pidió ("tabla de la plantilla").
- **Activar/desactivar como interruptor en la fila vs. botón con confirmación.** El interruptor es más rápido pero un clic accidental retira un producto de la venta; se prefiere botón + confirmación `Swal`.
- **Mantener Dashboard 2 en el menú**: no se pidió ("solo conservar el menú de dashboard"); se retira del menú, la ruta puede seguir existiendo (decisión de plan).

## Comportamiento por privilegio/estado
- **Privilegios:** hoy no existen roles; todo usuario autenticado ve y puede hacer todo en Catálogo. Nota: esto es solo UX; la verificación real de que el usuario puede crear/editar/desactivar corresponde al backend (`IsAuthenticated` ya es el permiso por defecto, `backend/config/settings/base.py:75-77`) y a `delivery-architect` si se quiere algo más fino. El frontend no es la barrera de seguridad.
- **Estado del producto:** inactivo se muestra con badge rojo y el botón cambia a "Activar"; el detalle y la edición siguen disponibles para inactivos (la edición no depende del estado).
- **Estados de pantalla:** lista con `loadingIndicator` mientras carga; mensaje "No hay productos" cuando el filtro/búsqueda no devuelve filas; error de red con aviso (`toastr`); formulario con botón "Guardar" deshabilitado mientras sea inválido o se esté enviando; errores de validación devueltos por el servidor (nombre vacío, precio inválido) se muestran en el campo correspondiente; producto inexistente en detalle/edición → aviso y retorno a la lista.
- **Textos:** contenido de las pantallas en español (consistente con los mensajes de login); solo el menú pasa por `translate`.

## Consecuencias
- Más simple: un menú de dos entradas; páginas con URL propia y enlazables; reutiliza `ngx-datatable`, `Swal` y `toastr` ya instalados, sin nuevas dependencias.
- Deuda aceptada: el menú queda en español/inglés/alemán mientras las pantallas de Catálogo están solo en español; las páginas de demo siguen accesibles por URL mientras no se retiren sus rutas de `app.routes.ts`; el búsqueda/filtro/paginación de la lista quedan sujetos al contrato de API que defina arquitectura (cliente vs. servidor).
- Dejan de ser alcanzables desde el menú: Dashboard 2 y todas las secciones de demo; el logo y el post-login siguen apuntando a `/dashboard/main`.
- Pendiente para arquitectura (no se decide aquí): campos exactos del producto (¿SKU? ¿moneda?), unicidad del nombre, paginación/filtros en servidor, y si activar/desactivar son endpoints separados.

## Ajustes de implementación (2026-10-08)
Decididos con el usuario al revisar las pantallas; no cambian el comportamiento definido arriba:
- Selector de estado y botón "+" van juntos en una fila a la derecha del buscador.
- Colores de las acciones de la tabla: **Ver** = color primario de la aplicación (`#6777ef`), **Editar** = amarillo (`#ffc107`), **Desactivar/Activar** = rojo (`#dc3545`, en ambos estados), con el icono centrado en el círculo.
- El campo de precio es de texto con `inputmode="decimal"` (acepta coma o punto, hasta 2 decimales) en vez de `type="number"`, para enviar el valor como string sin pasar por `float`.
- El idioma por defecto de la aplicación pasa a español (antes dependía del navegador); el menú se muestra como "Catálogo ▸ Producto". Cambio global, no solo de Catálogo.
