# DDR-pedido-pantalla-unica-creacion-detalle-pedido-en-curso: Detalle del pedido en preparación, listo y entregado

**Estado:** Propuesto
**Task relacionado:** TASK-pedido-pantalla-unica-creacion
**Fecha:** 2026-11-23

## Contexto
Con la creación en una sola pantalla, el pedido nace en `IN_PREPARATION` con todo cargado. La pantalla de detalle actual (paneles Entrega y Cobro, tarjetas de productos, importes, pagos y datos) está pensada para armar el pedido. La persona pidió una vista de consulta con acciones en la cabecera para los estados `IN_PREPARATION`, `READY` y `DELIVERED`.

## Pantallas/flujos afectados
`features/sales/pages/order-detail` para pedidos en `IN_PREPARATION`, `READY` y `DELIVERED`. Los pedidos `NEW` y `CANCELLED` conservan el detalle actual (edición de productos y descuento en NEW; aviso de cancelación).

## Componentes/patrones elegidos
Plantilla **Detalle** de `docs/design/design-system.md` (sección 5) con acciones de ciclo de vida:
1. **Cabecera:** `Pedido <código>` + badge de estado + badge de cobro, y a la derecha las acciones: botón primario del paso siguiente (`IN_PREPARATION` → «Marcar listo»; `READY` → «Marcar entregado», con el diálogo de entrega existente; `DELIVERED` → ninguno), **«Registrar pago»** (solo si el servidor permite cobrar), «Cancelar pedido» (outline, solo si el servidor lo permite) y «Volver a pedidos».
2. **Datos** (`dl.row`, cuatro columnas: etiqueta/valor × 2): Cliente · Canal de venta; Fecha del pedido · Fecha de entrega; Almacén (solo si el pedido tiene almacén). En `DELIVERED` se añade «Entrega real»; las notas se muestran solo si existen.
3. **Productos** (tabla de solo lectura): Producto · Precio unitario · Cantidad · Subtotal.
4. **Importes** a la derecha: Subtotal · Descuento · Total · Pagado · Saldo (valores del servidor; sin campos editables; el saldo en rojo si hay deuda y en verde si no; PLAN v4, AC-14).
5. **Pagos:** el listado de pagos existente en modo solo lectura (sin formulario embebido); en `DELIVERED` se conserva la tarjeta de salida de inventario.
6. **«Registrar pago» abre un modal** (`NgbModal`, patrón de `delivery-dialog`) con monto, método, fecha y referencia, saldo visible, errores del servidor por campo y clave de idempotencia por intento; al registrar, el modal se cierra y el detalle muestra el pedido actualizado.
7. «Marcar listo» llama a `POST /orders/{id}/ready/` y actualiza el estado en pantalla.

## Alternativas consideradas
- Mantener el formulario de pago embebido en la tarjeta: descartada, la persona pidió un modal.
- Reutilizar `app-order-items`/`app-order-summary`: descartadas, mezclan edición con vista; la vista de consulta es de solo lectura.
- Usar la nueva vista también para `NEW`: descartada, `NEW` aún se edita en el detalle.

## Comportamiento por privilegio/estado
Los botones salen de `allowedTransitions` y `canRegisterPayment` del servidor. Los avisos existentes (entregado con saldo, pagado pendiente de entrega, faltantes de configuración contable) se conservan sobre la vista. **El backend sigue siendo la barrera:** el estado, el cobro y la cancelación se validan en la API.

## Consecuencias
- Un pedido ya confirmado deja de poder editarse desde la interfaz (productos, descuento y «Editar datos»); la API sigue permitiéndolo. Si hiciera falta, se reabre como una decisión aparte.
- Los pagos solo se registran por el modal en estos estados.
