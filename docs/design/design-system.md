# Sistema de diseño PocketBiz

Fuente de verdad del lenguaje visual de `frontend/panel_admin/`. Lo leen `delivery-start` (al decidir pantallas), `delivery-build` (al implementarlas) y `delivery-publish` (al verificar consistencia). Los tokens del repositorio mandan: este documento los describe, no los redefine.

**Origen:** extraído del código el 2026-10-27 (`src/assets/scss/_variable.scss`, `skins/_white.scss`, `src/index.html`, `src/app/shared/`, y las pantallas de `features/products|customers|sales|expenses|reporting`) y de `DDR-pocketbiz-branding-logos-marca-y-color.md`. Si el código y este documento difieren, el código manda: corrige el documento en el mismo PR.

## 1. Reglas de oro

1. **Reutiliza antes de crear.** Usa un componente de `shared/` o de la plantilla Oreva (`frontend/panel_admin_doc/`). Una pantalla nueva copia la estructura de una existente (sección 5).
2. **Nada de colores, fuentes ni tamaños sueltos.** No escribas HEX en componentes. Usa clases de la plantilla (`btn-primary`, `col-green`, `text-danger`) o variables de `_variable.scss`.
3. **El color nunca va solo.** Estados llevan texto (y, si ya existe, icono). Los botones de solo icono llevan `title` y `aria-label`.
4. **Textos en español**, con "Bs" como moneda y fechas `dd/MM/yyyy HH:mm`.
5. **Un solo patrón por tipo de pantalla**: lista, formulario, detalle, dashboard/reporte.
6. Una desviación de este documento se justifica en el DDR de la tarea o en el PR.

## 2. Tokens

### Color

| Token | Valor | Uso |
|---|---|---|
| `primary` | `#1677FF` | Botón principal, enlaces, acción "ver", elementos activos. Fuente única: `$colors.primary` en `_variable.scss` y `$color-primary` en `skins/_white.scss` |
| `success` | `#54ca68` | Estados positivos (`col-green`) |
| `warning` | `#ffa426` | Alertas y pendientes (`col-orange`) |
| `danger` | `#fc544b` | Errores, estados negativos (`col-red`, `text-danger`) |
| `info` | `#3abaf4` | Información (`col-cyan`) |
| `secondary` / `muted` | `#6c757d` / `#98a6ad` | Texto secundario |
| `dark` | `#191d21` | Fondo del tema oscuro y del sidebar oscuro |
| `body` | `#f6f6f6` | Fondo de página |
| `white` | `#ffffff` | Tarjetas |
| Menú activo (light) | `#125AC4` | Solo ítem seleccionado del menú lateral, texto blanco |

Acciones de tabla (`shared/styles/_table-actions.scss`): ver = `#1677ff`, editar = `#ffc107`, desactivar/activar = `#dc3545`.

Contraste: `#1677FF` sobre blanco da ≈3,9:1. Úsalo en botones con texto blanco, enlaces y texto grande; no para párrafos largos.

### Tipografía

- Fuente: **Inter** 400/500/600/700, cargada en `index.html` (Google Fonts), respaldo `sans-serif`.
- Escala: la de Bootstrap 5 de la plantilla. Títulos de tarjeta con `<h4>`, título de página con `<h5 class="page-title">` en el breadcrumb, énfasis con `fw-bold`.

### Espaciado, forma y densidad

- Grilla Bootstrap 5; breakpoints `sm 576`, `md 768`, `lg 992`, `xl 1200`.
- Espaciado con utilidades Bootstrap/plantilla (`m-4`, `ms-2`, `p-10`, `gap-2`). No uses `px` sueltos para separar bloques.
- Tarjetas (`.card`) como contenedor de todo contenido principal.
- Tema claro por defecto. Existen tema oscuro y skins alternativos en el panel de configuración; las pantallas deben verse bien en claro y oscuro, y no dependen de skins.

### Marca

- Logo principal `assets/images/main-logo.png` (login, sidebar expandido); logo reducido `simple-logo.png` (sidebar contraído); favicon `pocketbiz.ico`; título de pestaña "PocketBiz".
- Avatar de usuario: iniciales, componente `app-user-avatar` (`shared/components/user-avatar`). No se guardan fotos.

## 3. Componentes reutilizables

| Necesidad | Usa | Dónde |
|---|---|---|
| Avatar con iniciales | `app-user-avatar` (`size`: `sm` o `xl`) | `shared/components/user-avatar` |
| Mostrar dinero | pipe `money` (`"70.00"` → `Bs 70.00`, vacío → `—`); no convierte ni redondea | `shared/pipes/money.pipe.ts` |
| Canal de venta | modelo compartido | `shared/models/sales-channel.ts` |
| Paginación | modelo `Page` | `shared/models/page.ts` |
| Botones de acción en tabla | clases `btn btn-tbl-edit btn-tbl-view\|update\|toggle h-auto` | `shared/styles/_table-actions.scss` |
| Estado de pedido / de pago | `app-order-status-badge`, `app-payment-status-badge` | `features/sales/components/` |
| Tabla | `ngx-datatable` con clase `material`, paginación externa | plantilla |
| Selector con búsqueda | `ng-select` | plantilla |

Si un componente se necesita en un segundo módulo, muévelo a `shared/` en lugar de copiarlo.

### Badges de estado

Formato único: `<div class="badge-outline col-<color>">Texto</div>`.

| Estado | Color |
|---|---|
| Activo / Entregado / Pagado | `col-green` |
| Inactivo / Cancelado | `col-red` |
| Pedido nuevo | `col-blue` |
| En preparación / Pago pendiente | `col-orange` |
| Listo | `col-indigo` |
| Pago parcial | `col-cyan` |
| Reembolsado | `col-purple` |

### Botones

| Tipo | Clase | Ejemplo |
|---|---|---|
| Acción principal (una por pantalla) | `btn btn-primary` | Guardar, Editar |
| Alta rápida en cabecera de lista | `btn btn-icon icon-left btn-primary rounded-button` con icono `add` | Nuevo producto |
| Acción secundaria/cancelar | `btn btn-light` | Cancelar, Volver |
| Acción de estado (activar/desactivar) | `btn btn-warning` | Desactivar |

Al guardar se deshabilita el botón (`[disabled]="form.invalid || saving || loading"`).

## 4. Estados que toda pantalla debe cubrir

| Estado | Tratamiento |
|---|---|
| Cargando | `loadingIndicator` en tablas; texto "Cargando…" en detalle |
| Vacío | Mensaje en español en `[messages]` de la tabla; nunca una tabla en blanco sin explicación |
| Error de validación | `<small class="form-text text-danger">` bajo el campo, con el mensaje del servidor si existe |
| Error de servidor | Mensaje visible, nunca solo en consola |
| Éxito | Confirmación visible o navegación a la pantalla de detalle/lista |
| Sin permiso | El frontend no es la barrera de seguridad: el backend responde 403 y la UI lo muestra |

## 5. Plantillas de pantalla

Todas empiezan con `<section class="main-content">` y un breadcrumb: título (`h5.page-title`), icono de inicio hacia `/dashboard/main`, módulo y pantalla.

### Lista (referencia: `features/products/pages/product-list`)
- Una `.card` con cabecera: título `<h2><strong>`, buscador (`search-field`, con `label` y `aria-label`), filtro de estado (`form-select`, por defecto **Activos**) y botón "+".
- `ngx-datatable` con columnas: nombre (enlace en negrita al detalle), datos, **Estado** (badge) y **Acciones** (ver, editar, activar/desactivar).
- Paginación externa (servidor), sin ordenamiento en cliente.

### Formulario (referencia: `product-form`)
- `.card` con `card-header` (`h4`) y `card-body`; `form.register-form m-4` con Reactive Forms.
- Campos en `.form-group col-md-*` con `label` asociado; obligatorios marcados con `<span class="text-danger">*</span>`.
- Pie: `Guardar` (primario) y `Cancelar` (`btn-light ms-2`), que vuelve al detalle (edición) o a la lista (alta).
- Los errores del servidor se muestran por campo.

### Detalle (referencia: `product-detail`)
- `.card` con `h4` = nombre del registro; datos en `<dl class="row m-4">` con `dt.col-sm-3` / `dd.col-sm-9`.
- Estado como badge; fechas `dd/MM/yyyy HH:mm`; texto de relleno "Sin …" cuando no hay dato.
- Acciones bajo los datos: Editar (primario), Activar/Desactivar (`btn-warning`), Volver (`btn-light`).

### Dashboard y reportes (referencia: `features/reporting`)
- Selector de periodo arriba (`app-period-selector`), tarjetas de cifras con `app-report-card` y listas/tablas debajo; los textos de apoyo van en `<small class="text-muted">` y los vacíos dicen "Sin datos para este periodo."
- Etiquetas de negocio exactas: **"Ganancia estimada"** (nunca "utilidad" o "ganancia real").

### Formulario de configuración con pestañas (referencia: `features/settings/pages/module-settings`)
- `.card` con `card-header` (`h4` «Configuración de <módulo>») y pestañas «General» / «Historial de cambios» (`nav nav-tabs`, `role="tablist"`).
- General: una fila por ajuste con `label`, control, descripción del efecto (`small.text-muted`), «Valor predeterminado» con «Restablecer» y error junto al campo (`small.text-danger`). Pie: «Guardar cambios» (primario) y «Cancelar cambios» (`btn-light`), ambos deshabilitados sin cambios; aviso de salida con `unsavedChangesGuard` + `beforeunload`.
- Historial (`app-settings-history`): filtros Desde/Hasta/Ajuste, tabla apilada en móvil, paginación `ngb-pagination`; vacío «Sin cambios registrados.».

### Configuración con listados en pestañas y diálogo (referencia: `features/inventory/pages/inventory-configuration`)
- `.card` con `h4` y `nav-tabs` (`role="tablist"`); cada pestaña es un listado con buscador por nombre, filtro de estado (por defecto **Activos/Activas**) y botón «+», en tabla Bootstrap simple apilada en móvil (`inventory/components/_inventory-table.scss`).
- Alta/edición en diálogo (`NgbModal`, patrón de `category-dialog`); sin eliminar: los registros usados se desactivan. Los bloqueos del servidor (409) se muestran en `alert alert-warning` sobre la tabla con el motivo, y un registro bloqueado deshabilita sus campos con `small.text-muted` que explica por qué.

### Sección condicionada por módulo en un formulario (referencia: `product-form`, bloque «Inventario»)
- `h5` de sección, interruptor `form-check form-switch` y selector dependiente (`form-select`) que aparece solo si el interruptor está activo. Todo el bloque se renderiza únicamente si el módulo está habilitado (`ModulesService.enabledKeys$`); lista y detalle añaden columnas/filas solo en ese caso. Un 409 de regla de negocio se muestra con `alert alert-warning` sin perder lo escrito.

### Formulario con líneas y paso de resumen (referencia: `features/inventory/pages/stock-opening`)
- Cabecera de campos + tabla de líneas (selector sin repetir elementos ya elegidos, datos de solo lectura derivados, campo numérico, quitar) y «+ Agregar línea». Una línea con problema de negocio se marca con `table-warning` y se explica en un `alert alert-warning`; mientras exista, no se avanza.
- «Revisar resumen» cambia, en la misma ruta, a un `card` con `dl.row` y tabla de solo lectura; «Confirmar» (primario) y «Volver a editar» (`btn-light`). Confirmar se deshabilita y muestra «Registrando…» mientras envía; el formulario genera una clave de idempotencia al abrirse y la reutiliza en cada reintento. Cancelar vuelve a la lista sin escribir y con cambios pendientes usa `unsavedChangesGuard`.

#### Variante de un solo paso con totales calculados (referencia: `features/purchases/pages/purchase-form`)
- Misma plantilla, sin «Revisar resumen» cuando guardar no es irreversible (un borrador): cabecera + tabla de líneas con «+ Agregar línea», subtotal por línea y fila **Total** de solo lectura (`MoneyPipe`) bajo la tabla. Los importes que se muestran mientras se escribe se calculan en una función pura de aritmética entera que replica la regla del servidor; tras guardar manda el servidor.
- Los errores de una línea (`small.text-danger` bajo su campo, fila `table-warning` si vienen del servidor) se muestran junto a la línea y nunca borran lo escrito. Si falta un dato maestro (p. ej. proveedores), el selector ofrece «Crear …» en un diálogo (`NgbModal`) en vez de salir de la pantalla. Salir con cambios usa `unsavedChangesGuard`.

### Lista de solo lectura con filtros (referencia: `features/inventory/pages/movement-list`)
- Misma estructura que Lista, sin botón «+» ni acciones Editar/Eliminar (registros inmutables): breadcrumb, `.card`, formulario de filtros en fila (`label` + `input type=date`/`form-select`, «Limpiar filtros»), `ngx-datatable` con paginación del servidor. Las cantidades de entrada y salida van en columnas separadas, alineadas a la derecha, con «—» en la que no aplica y la unidad en su propia columna. Error de servidor en `alert alert-danger` con «Reintentar». El enlace a un documento de otro módulo solo se muestra si el servidor indica que ese módulo está habilitado y existe su pantalla. El detalle sigue la plantilla Detalle (`dl`) y enlaza registros relacionados (contramovimientos). Si la lista tiene filtros que la persona quiere conservar al entrar a un detalle, se guardan en un servicio en memoria (`StockFiltersState`, referencia: `stock-list`) y se restauran al volver. Los usos de un producto se muestran como badges con texto («Comprable» azul, «Vendible» verde, «Sin usos» gris) y la categoría sin asignar como «Sin clasificar» gris.

### Detalle con historial embebido (referencia: `features/inventory/pages/stock-detail`)
- Plantilla Detalle (`.card`, `h4` = nombre, `dl.row`) más acciones bajo los datos (la principal en `btn-primary`, una acción condicionada por regla de negocio que, si no aplica, se oculta y se explica con `small.text-muted`) y una sección `h5` con el historial: tabla Bootstrap apilada (`_inventory-table.scss`), 10 filas por página con `ngb-pagination`, vacío con mensaje (nunca error), y enlace «Ver detalle» a cada registro. Un saldo negativo se marca con texto («Negativo», `badge-outline col-red`) además del color `text-danger`.

### Autenticación (referencia: `signin`, `signup`)
- Tarjeta centrada y angosta (≈480–520 px) con `main-logo.png` y `alt="PocketBiz"`; sin imagen lateral en login.

## 6. Menú y layout

- Submenú de Compras: «Inicio» (`/purchases`, «Próximamente»), «Proveedores» (`/purchases/suppliers`, lista, `/new`, `/:id/edit` y detalle `/:id`, PB-COM-001; plantillas Lista, Formulario y Detalle de clientes, con «Ver compras» hacia `/purchases?supplierId=<id>`) y «Configuración» (`/purchases/settings`). Ver `DDR-gestionar-proveedores-pantallas-proveedores`.
- Submenú de Inventario: «Inicio», «Almacenes y unidades» (`/inventory/configuration`), «Existencias» (`/inventory/stock`, con detalle `/inventory/stock/:productId/:warehouseId`, PB-INV-005), «Movimientos» (`/inventory/movements`, solo lectura, PB-INV-004), «Ajustes de existencias» (`/inventory/adjustments`, lista, `/new` y detalle de solo lectura, PB-INV-006) y «Ajustes» (`/inventory/settings`, PB-CFG-001). El formulario de ajuste sigue el patrón «formulario con revisión y confirmación de envío único» con la variante de reconfirmación: si el saldo cambió (409 `balance_changed`) vuelve al resumen con el saldo nuevo y la acción de confirmar queda explícita.

- Sidebar: logo según estado (expandido/contraído), avatar con iniciales, nombre y apellido, nombre de la empresa. Ítems principales: Dashboard, Catálogo (Producto), Cliente, Pedidos, Gastos (Gastos, Categorías), Reportes (textos en `assets/i18n/es.json`).
- Header: solo el menú de usuario (nombre, empresa y cerrar sesión). Sin búsqueda, mensajes ni notificaciones.
- El menú es dinámico: cada ítem de `assets/data/routes.json` puede llevar `module` y solo se muestra si la empresa tiene ese módulo habilitado (Dashboard y Reportes → `reporting`). Ventas, Compras e Inventario son submenús con su «Configuración» (`/sales/settings`, `/purchases/settings`, `/inventory/settings`). Al final hay «Configuración › Módulos» (`/settings/modules`, con pestañas General e Historial, pantalla de lista con tabla Bootstrap simple y diálogo de confirmación) y, si están habilitados, «Compras» e «Inventario» (pantalla «Próximamente»).
- Un módulo deshabilitado (URL guardada o 403 `module_disabled` de la API) lleva a `/module-disabled`: pantalla simple «Módulo no habilitado» con «Volver al inicio» (DDR-bloquear-api-modulos-deshabilitados-pantalla-no-habilitado).
- Rutas por módulo: `catalog/products`, `customers`, `sales/orders`, `expenses`, `reports`; cada una con `''`, `new`, `:id`, `:id/edit`.

## 7. Accesibilidad mínima

- Todo `input` con `label` (`for`/`id`) o `aria-label`.
- Botones de solo icono: `title` y `aria-label`.
- Iconos decorativos: `aria-hidden="true"`.
- Foco visible; navegación por teclado en formularios y diálogos.
- Contraste mínimo 4,5:1 para texto normal; ver nota del primario en la sección 2.

## 8. Checklist para `delivery-publish`

Una pantalla nueva o modificada pasa si:

- [ ] Sigue la plantilla de su tipo (sección 5): breadcrumb, `.card`, mismos bloques y orden.
- [ ] No introduce HEX, fuentes ni tamaños propios; usa clases/variables existentes.
- [ ] Usa `money`, `app-user-avatar`, badges y botones de tabla compartidos en lugar de copias.
- [ ] Cubre los estados de la sección 4.
- [ ] Cumple la accesibilidad mínima (sección 7).
- [ ] Se ve bien en móvil (≈390 px) y en escritorio (≈1440 px), en tema claro y oscuro.
- [ ] Textos en español, moneda "Bs", fechas `dd/MM/yyyy HH:mm`.

## 9. Bloque para prompts de Stitch (flujo UX/UI opcional)

> Panel administrativo de pequeño negocio, marca PocketBiz. Color primario #1677FF, éxito #54ca68, advertencia #ffa426, peligro #fc544b, fondo #f6f6f6, tarjetas blancas, tema oscuro con fondo #191d21. Tipografía Inter. Bootstrap 5, tarjetas con título, tablas con badges de estado outline, botones de acción circulares en tabla (ver azul, editar amarillo, desactivar rojo). Textos en español, moneda Bs. Escritorio 1440 px y móvil 390 px.

## 10. Deuda visual conocida

- La plantilla conserva pantallas demo (calendario, tablas avanzadas, etc.) con la marca y el estilo originales; no son parte del producto.
- Los skins alternativos del panel de configuración conservan sus propios colores y pueden alejarse de la paleta de marca.
- Hay textos de la plantilla Oreva sin traducir fuera de las pantallas del producto (por ejemplo "Welcome to Oreva" en el header).
- Algunos HEX de las acciones de tabla están escritos a mano en `_table-actions.scss`; deberían apuntar a variables.
