# DDR-cancelar-ventas-registrar-devoluciones-acciones-y-vista-previa: Acciones «Cancelar venta» / «Registrar devolución» y su historial

**Estado:** Propuesto
**Task relacionado:** TASK-cancelar-ventas-registrar-devoluciones
**Fecha:** 2026-11-24

## Contexto
El detalle del pedido ya ofrece «Cancelar» (diálogo SweetAlert con motivo) antes de entregar. Falta la devolución tras entregar y mostrar quién/cuándo/por qué y los vínculos a movimientos y asientos.

## Pantallas/flujos afectados
Solo `features/sales/pages/order-detail`:
1. **Cancelar venta** (estados NEW/IN_PREPARATION/READY): se mantiene el botón; se mantiene el diálogo de motivo (SweetAlert) y, si hay cobros, una segunda confirmación obligatoria con el total cobrado y el botón «Ya devolví el dinero» (el servidor exige `refund_acknowledged`). Aprobado por el usuario (REV-04, PLAN v2).
2. **Registrar devolución** (estado DELIVERED): botón en la cabecera → diálogo con motivo obligatorio, tabla de productos y cantidades (todas, solo lectura: devolución total), efecto sobre existencias (almacén y unidades a reingresar o «sin salida de inventario»), efecto contable (asientos que se contrarrestarán, con su fecha de hoy) y la casilla de reembolso si hay cobros. El efecto sale de un endpoint de vista previa solo lectura.
3. **Sección «Cancelación / Devolución»** en el detalle (cuando el pedido está CANCELLED o RETURNED): fecha, usuario, motivo, reembolso, enlaces a movimientos de inventario (original y reverso) y a asientos (original y contrasiento).

## Componentes/patrones elegidos
Plantilla «Detalle de documento en curso con acciones en la cabecera» (design-system §5, ref. `order-detail`) y «Diálogo de acción irreversible con motivo» (§5, ref. `receipt-revert-dialog`) con `NgbModal` en lugar de SweetAlert para el diálogo de devolución, por necesitar tabla y vista previa. Badge de estado «Devuelto» siguiendo §3 «Badges de estado».

## Alternativas consideradas
- SweetAlert también para devolver: descartado, no admite tabla/vista previa reutilizable ni estados de carga/error.
- Página propia de devolución: descartada, innecesaria para una devolución total.

## Comportamiento por privilegio/estado
Los botones se muestran según `allowedTransitions` (`cancel`, `return`) que informa el backend; el backend aplica rol admin, empresa y estado. Estados del diálogo: cargando vista previa, error (409 con mensaje accionable: período cerrado, configuración contable faltante), éxito (toast y recarga del detalle). Botón confirmar deshabilitado mientras falte el motivo o la casilla de reembolso (si hay cobros). Textos con `translate` (es/en/pt).

## Consecuencias
Un diálogo nuevo; la devolución parcial queda fuera (la tabla es solo lectura y se podrá volver editable).
