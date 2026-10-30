# DDR-ventas-inventario-salida-al-entregar-dialogo-entrega-y-detalle: Diálogo de entrega, salida en el pedido y movimientos por venta

**Estado:** Propuesto
**Task relacionado:** TASK-ventas-inventario-salida-al-entregar
**Fecha:** 2026-10-29

## Contexto
La entrega de un pedido con productos que controlan stock necesita elegir un almacén y mostrar el efecto en las existencias antes de confirmar. Hoy «Marcar como entregado» abre un SweetAlert con solo la fecha (`order-detail.component.ts:185-202`). No se agrega menú ni formulario de movimiento manual.

## Pantallas/flujos afectados
1. **Ventas → Pedidos → Detalle** (`/pocketbiz/sales/orders/:id`): acción «Marcar como entregado», diálogo nuevo y tarjeta «Salida de inventario».
2. **Inventario → Movimientos** (lista y detalle): etiqueta «Salida por venta», filtro por pedido y enlace de vuelta al pedido.

## Componentes/patrones elegidos
- **Diálogo de entrega** (`features/sales/components/delivery-dialog`): `NgbModal` con el patrón de `warehouse-dialog` (design-system sección 3 y 5, «Configuración con listados y diálogo»). Contenido, de arriba abajo:
  - Encabezado «Marcar como entregado» y la referencia del pedido (`P-XXXXXXXX`) más cliente si existe.
  - **Fecha de entrega** (`input type=date`, hoy por defecto, `max` hoy): se conserva porque `deliver` ya la admite.
  - **Almacén de salida**: `select.form-select` con los almacenes activos; con uno solo se muestra como texto de solo lectura. Preselección: el único activo o el `is_default`.
  - **Tabla** `table table-sm`: Producto · Cantidad a entregar · Unidad (base) · Existencia actual · Saldo proyectado. El saldo negativo va en `text-danger` con icono y texto («negativo»), nunca solo por color.
  - **Avisos** (`alert` de Bootstrap, `role="alert"`):
    - bloqueo activo y hay faltante → `alert-danger` «Existencia insuficiente en <almacén>» listando las líneas; **«Confirmar entrega» queda deshabilitado**; sin «Continuar de todos modos` ni enlace a cambiar la política;
    - negativos permitidos y saldo proyectado < 0 → `alert-warning` «Esta entrega dejará saldo negativo en N producto(s). Es la política de inventario configurada»;
    - sin almacén activo → `alert-warning` que explica qué falta («Crea o activa un almacén en Inventario → Configuración → Almacenes») y deshabilita la confirmación.
  - Pie: «Cancelar» (secundario) y «Confirmar entrega» (primario). Durante el envío «Confirmar entrega» se deshabilita y muestra «Confirmando…»; los datos (fecha, almacén) se conservan si falla.
- **Pedido sin ítems controlados, o Inventario deshabilitado:** se mantiene el SweetAlert actual (confirmación habitual con fecha). La decisión sale de `delivery-preview` (`requires_stock_output`).
- **Detalle posterior** (pedido `DELIVERED` con `stock_output`): tarjeta «Salida de inventario» bajo los ítems con referencia, almacén, fecha y tabla (Producto · Cantidad · Unidad) y botón «Ver movimientos» (`routerLink` a `/pocketbiz/inventory/movements?source_type=sales_order&source_id=<id>`), solo si Inventario está habilitado. Estado logístico (`order-status-badge`) y de pago (`payment-status-badge`) siguen en componentes separados y no se mezclan.
- **Movimientos:** la columna Tipo muestra «Salida por venta» para `out` + `sales_order` (resto: «Entrada»/«Salida»). Filtro por pedido: al llegar con `source_id` se muestra un chip «Pedido P-XXXX ✕» sobre la tabla que lo quita; los filtros existentes se mantienen. En el detalle del movimiento se conserva el enlace al pedido que ya existe (`SOURCE_ROUTES.sales_order`), visible solo si `source.available`.
- Plantilla de pantalla: **detalle** (design-system sección 5) para el pedido; **lista con filtros** para Movimientos. Sin componentes fuera del sistema de diseño.

## Estados
- *Cargando preview:* spinner en el cuerpo del diálogo; acción deshabilitada.
- *Error al cargar preview:* `alert-danger` con «Reintentar»; el pedido no cambia.
- *Cambio de almacén:* se vuelve a pedir el preview con ese almacén (tabla en carga); mientras tanto la confirmación está deshabilitada.
- *409 `insufficient_stock` al confirmar:* el diálogo sigue abierto, la tabla se actualiza con los valores vigentes del servidor y aparece el `alert-danger`; el pedido permanece en «Listo».
- *409 de transición inválida (otra pestaña ya lo entregó):* se cierra el diálogo, se avisa y se recarga el pedido.
- *400 de almacén (otro/inactivo):* error bajo el selector.
- *Éxito:* se cierra, toast «Pedido entregado» y el detalle muestra la tarjeta de salida.

## Alternativas consideradas
- **SweetAlert con HTML para la tabla:** reutiliza lo existente, pero no admite selector reactivo ni foco/teclado accesibles para una tabla con estados; descartada para el caso con stock (se mantiene para el simple).
- **Página dedicada «Confirmar entrega»:** más espacio, pero agrega una ruta y rompe el flujo corto de la acción; descartada.
- **Vista en Inventario para ver salidas del pedido:** ya cubierta por el filtro de Movimientos; evita una pantalla duplicada.

## Comportamiento por privilegio/estado
- «Marcar como entregado» aparece solo si `allowed_transitions` incluye `deliver` (lo decide el servidor). El backend es la barrera: valida estado, empresa, almacén activo de la empresa, política y saldo al confirmar; el frontend solo informa (el saldo mostrado es una foto).
- Quien no tenga el módulo Inventario habilitado nunca ve almacén ni tarjeta de salida.
- La tarjeta y el enlace a Movimientos dependen de `stock_output` y del módulo Inventario habilitado; el enlace desde un movimiento al pedido depende de `source.available` (Ventas habilitado).

## Consecuencias
Se introduce un diálogo con tabla en Ventas (patrón nuevo para ese feature, no para el sistema). Deuda aceptada: el «Ver movimientos» filtra por query string y no hay un componente de chip de filtros compartido todavía (se implementa local en la lista de Movimientos). No se propone cambio a `design-system.md`.
