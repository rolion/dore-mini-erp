# DDR-pedido-pantalla-unica-creacion-formulario-unico: Pantalla única de creación de pedido

**Estado:** Propuesto
**Task relacionado:** TASK-pedido-pantalla-unica-creacion
**Fecha:** 2026-11-23

## Contexto
Crear un pedido exige hoy dos pantallas: datos (`order-form`) y luego detalle (productos, descuento, «Iniciar preparación»). La persona pidió una sola pantalla con la estructura de cabecera, detalle y totales, y que el botón final cree el pedido ya en preparación.

## Pantallas/flujos afectados
- **Nueva:** `features/sales/pages/order-create` en la ruta `/pocketbiz/sales/orders/new` (reemplaza a `OrderFormComponent` en esa ruta).
- **Sin cambios de ruta:** `:id/edit` sigue usando `OrderFormComponent` (editar los datos de un pedido NEW existente) y `:id` el detalle.
- **Detalle:** muestra el almacén del pedido cuando existe (fila nueva en el resumen) y el diálogo de entrega lo preselecciona.

## Componentes/patrones elegidos
Plantilla **«Variante de un solo paso con totales calculados»** de `docs/design/design-system.md` (sección 5, referencia `features/purchases/pages/purchase-form`), con la estructura pedida:

1. **Cabecera** (`form.register-form m-4`, Reactive Forms, `.form-group col-md-6`):
   - Fila 1: Cliente (`ng-select` con búsqueda y «Nuevo cliente», opcional; reutiliza el de `order-form`) · Canal de venta (`select.form-select`, obligatorio, precargado con el canal predeterminado de la empresa).
   - Fila 2: Fecha del pedido (`input[type=date]`, obligatoria, hoy por defecto) · Fecha de entrega (`input[type=date]`, opcional).
   - Fila 3: Almacén (`ng-select`/`form-select`), **visible solo si Inventario está habilitado**; obligatorio si algún producto de la tabla controla stock; preselecciona el único activo o el predeterminado. Fila de Notas (textarea opcional) debajo.
2. **Sección «Detalle del pedido»** (`h5`): fila `Producto (ng-select, "nombre · precio")` · `Cantidad (input number, entero ≥ 1)` · `Agregar`. Enter en cantidad agrega. Un producto ya presente **suma** la cantidad a su fila (no duplica filas).
3. **Tabla de productos** (`table.table-striped`, apilada en móvil): Producto · Precio unitario · Cantidad (input editable) · Subtotal (`MoneyPipe`) · Quitar (`btn-danger` con icono y `aria-label`). Una línea con problema de stock se marca `table-warning` y se explica en `alert alert-warning` (disponible vs. pedido).
4. **Totales**, alineados a la derecha bajo la tabla: Subtotal (solo lectura) · Descuento (`input` monetario; ayuda «Máximo permitido: X % del subtotal (Bs …)» con el tope de Ventas) · **Total** (solo lectura, destacado) · botón **Iniciar preparación** (primario, a la derecha, bajo los totales) y `Cancelar` (`btn-light ms-2`) que vuelve a la lista.
5. Los importes mostrados mientras se escribe vienen de una función pura de aritmética entera (centavos) que replica la regla del servidor; tras crear manda el servidor.

Sin componente nuevo reutilizable: no se propone cambiar `design-system.md`, salvo añadir `order-create` como segunda referencia de la variante «un solo paso».

## Alternativas consideradas
- **Mantener dos pantallas y solo mejorar el detalle**: descartada, es lo que la persona quiere eliminar.
- **Wizard en pasos (datos → detalle → resumen)**: descartada; añade pasos y la persona pidió una pantalla.
- **Crear el pedido NEW en el servidor al abrir la pantalla y editarlo en vivo**: descartada; deja pedidos huérfanos si se abandona y repite el modelo de dos fases.
- **Reutilizar `app-order-items` y `app-order-summary`**: descartada; operan sobre un `Order` ya persistido y emiten un evento por acción; la pantalla nueva trabaja sobre un borrador local.

## Comportamiento por privilegio/estado
- **Estados:** cargando (clientes, productos, almacenes y configuración: selectores con `loading`); vacío (tabla sin productos: «Agregue al menos un producto» y botón deshabilitado); error (400 por campo bajo cada control; 409 `insufficient_stock` en `alert alert-warning` con las líneas afectadas; otros errores en `toastr`); éxito (toast «Pedido en preparación» y navegación al detalle).
- **Botón «Iniciar preparación»:** deshabilitado sin productos, con el formulario inválido, mientras envía («Creando…») o con descuento sobre el tope. Salir con datos escritos usa `unsavedChangesGuard`.
- **Módulos:** Clientes deshabilitado → sin combobox de cliente; Inventario deshabilitado → sin combobox de almacén ni validación de stock.
- **Lo que debe aplicar el backend (el frontend no es la barrera):** tope de descuento, producto activo y vendible, cliente activo, ≥ 1 producto, no duplicados, almacén válido y activo, stock suficiente salvo política de stock negativo, aislamiento por empresa y módulo `sales` habilitado.

## Consecuencias
- La creación en dos pasos desaparece del alta; el detalle conserva edición de productos/descuento para pedidos NEW antiguos.
- Deuda aceptada: el precio mostrado puede diferir del que fije el servidor si el catálogo cambia durante la edición; el stock no se reserva.
- Todos los textos nuevos con claves i18n en es/en/pt.
