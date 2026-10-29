# DDR-compras-borrador-crear-editar-pantallas-compras: Lista, formulario con líneas y detalle de compras en borrador

**Estado:** Propuesto
**Task relacionado:** TASK-compras-borrador-crear-editar
**Fecha:** 2026-10-29

## Contexto
PB-COM-002 pide registrar una compra en borrador con proveedor, fecha, líneas de producto y total calculado. El sistema de diseño ya cubre lo necesario: plantilla **Formulario con líneas** (`docs/design/design-system.md` §5, referencia `features/inventory/pages/stock-opening`), **Lista** y **Detalle**. La selección de proveedor y de producto reutiliza los patrones de `features/sales/pages/order-form` (ng-select con typeahead y pie «+ Nuevo …») y `order-items`.

## Pantallas/flujos afectados
- **Menú**: en Compras, «Inicio» pasa a llamarse **«Compras»** (`/pocketbiz/purchases`) y deja de ser «Próximamente»; siguen «Proveedores» y «Configuración». Texto `MENUITEMS.PURCHASES.LIST.PURCHASES` en es/en/de (`es`: «Compras»).
- **Lista** `/purchases` (acepta `?supplierId=<id>`, destino de «Ver compras» de Proveedores).
- **Formulario** `/purchases/new` y `/purchases/:id/edit` (mismo componente).
- **Detalle** `/purchases/:id` (solo lectura).
- **Diálogo «Nuevo proveedor»** desde el selector de proveedor del formulario.

## Componentes/patrones elegidos
Todas las pantallas empiezan con `<section class="main-content">` y breadcrumb (Compras › Nueva compra / Editar compra).

**Lista** (plantilla Lista): `.card` con título «Compras», filtro de proveedor (cuando llega `supplierId` se muestra un chip «Proveedor: X» con «Quitar filtro»), botón «+ Nueva compra». `ngx-datatable` con Fecha (`dd/MM/yyyy`), Proveedor, Referencia externa, Total (`MoneyPipe`, alineado a la derecha), Estado (badge «Borrador») y Acciones (ver, editar). Paginación en servidor. Vacío: «Aún no hay compras. Crea la primera con «Nueva compra».»; vacío con filtro: «No hay compras para este proveedor.». Carga: `loadingIndicator`; error: `alert alert-danger` con «Reintentar».

**Formulario** (plantilla Formulario con líneas; un solo paso, sin «Revisar resumen» porque guardar un borrador no es irreversible):
- `.card` con `h4` («Nueva compra» / «Editar compra») y `form.register-form m-4` (Reactive Forms, `FormArray` para las líneas).
- Cabecera (`.form-group col-md-6`): **Proveedor*** (ng-select, solo activos, búsqueda por nombre, pie «+ Nuevo proveedor»), **Fecha de compra*** (`type=date`, hoy por defecto), **Referencia externa** (opcional, ≤ 100), **Notas** (opcional, ≤ 2000, `textarea`). Etiqueta fija «Moneda: BOB» junto al total.
- Sin proveedores activos: el selector muestra «No hay proveedores activos.» y un botón «Crear proveedor» que abre el diálogo; al guardarlo queda seleccionado. Como no se abandona la pantalla, nada de lo escrito se pierde.
- **Líneas** (tabla Bootstrap apilada en móvil, como `stock-opening`): Producto (ng-select de productos activos, búsqueda por nombre, sin repetir los ya elegidos), Unidad base (solo lectura; «—» si no tiene), Cantidad (`type=number`, `step` 0.001, o 1 si la unidad no admite fracciones), Precio unitario (`type=number`, `step=0.01`), Subtotal (solo lectura, `MoneyPipe`) y Quitar (icono). Pie de tabla: «+ Agregar línea». Fila **Total** (solo lectura) bajo la tabla.
- Cantidad o precio inválidos (cliente o servidor) se marcan con `text-danger` en una `small` **bajo el campo de su línea** y la fila con `table-warning`; el resto de líneas y la cabecera conservan lo escrito. Errores de cabecera del servidor, bajo su campo. Un error general (red/500) en `alert alert-danger`.
- No existen campos de impuestos, descuentos ni costos adicionales; tampoco el total es editable.
- Pie: **Guardar borrador** (primario; deshabilitado mientras guarda → «Guardando…» y si el formulario es inválido) y **Cancelar** (`btn-light ms-2`), que vuelve a la lista (alta) o al detalle (edición). Con cambios sin guardar, `unsavedChangesGuard` pide confirmación al salir.
- Tras guardar: `toastr` «Compra guardada» y navegación al detalle.
- «Confirmar» no se dibuja en esta task (no hay acción detrás); el detalle lo incorporará la task de confirmación.

**Detalle** (plantilla Detalle): `h4` «Compra del dd/MM/yyyy»; `dl.row` con Proveedor, Fecha, Referencia externa («Sin referencia»), Notas («Sin notas»), Estado (badge «Borrador»), Moneda (BOB), Creada/Actualizada; tabla de solo lectura de líneas (Producto, Unidad, Cantidad, Precio unitario, Subtotal) y Total. Acciones: **Editar** (primario, solo borrador) y **Volver** (`btn-light`). Un proveedor desactivado se sigue mostrando con su nombre.

**Diálogo «Nuevo proveedor»** (patrón `CustomerQuickCreateService`, `NgbModal`): Nombre* y, opcionales, Identificación, Teléfono y Correo; errores bajo cada campo; «Guardar» / «Cancelar». Reutiliza `SuppliersApiService`.

Estados cubiertos (design-system §4): cargando, vacío, error de validación por campo y por línea, error de servidor visible, éxito con toast y navegación.

## Alternativas consideradas
1. **Enlace a `/purchases/suppliers/new` y volver con el borrador guardado en `sessionStorage`**: es lo que sugiere literalmente «conservar el formulario al volver», pero exige serializar/restaurar el formulario completo y un parámetro de retorno. Descartada por frágil; el diálogo cumple el criterio (el formulario nunca se descarta) con menos código y es el patrón ya usado en Ventas.
2. **Dos pasos (cabecera, luego líneas en el detalle) como Ventas**: descartada, el requerimiento pide formulario único con líneas y total visible mientras se edita.
3. **Subtotales solo tras guardar (sin cálculo en el navegador)**: descartada, el requerimiento pide ver subtotal y total mientras se editan las líneas. Se calcula con una función pura con aritmética entera que replica la regla del servidor; el servidor sigue siendo la fuente de verdad.
4. **Incluir también Confirmar y Cancelar compra**: fuera de alcance (tasks posteriores).

## Comportamiento por privilegio/estado
- Visible solo con el módulo `purchases` habilitado (`moduleGuard`, menú por `module`). Un borrador es editable; cualquier otro estado futuro oculta «Editar».
- **El frontend no es la barrera de seguridad**: el backend exige `required_modules = ('purchases',)`, aísla por `company_id`, valida proveedor activo, producto activo, cantidad > 0, precio ≥ 0, duplicados y que el borrador sea editable, y responde 403/404/400. Los ids de otra empresa responden como inexistentes.

## Consecuencias
- Lista y detalle son mínimos a propósito; los filtros, búsqueda por referencia y acciones de ciclo de vida llegan con las tasks de Compras siguientes.
- El submenú cambia de «Inicio» a «Compras» y se actualiza `sidebar-menu.spec.ts`.
- Se añade a `design-system.md` §5 una nota a la plantilla «Formulario con líneas» (variante de un solo paso con totales calculados y errores por línea) — misma plantilla, sin componente compartido nuevo. Duplicación del selector de producto con `order-items` aceptada (features independientes).
