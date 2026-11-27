# ADR-cancelar-ventas-registrar-devoluciones-reversion-orquestada-y-registro: Reversión orquestada desde Sales y registro de la anulación

**Estado:** Propuesto
**Task relacionado:** TASK-cancelar-ventas-registrar-devoluciones
**Fecha:** 2026-11-24

## Contexto
Cancelar (con cobros) y devolver deben deshacer, en una sola transacción, existencias, costo, asientos y el pedido, sin duplicar con reintentos o concurrencia. Las fachadas de Inventario y Accounting ya ofrecen reversiones idempotentes; Costeo no tiene reversa de salidas; el pedido no guarda quién, ni los vínculos.

## Decisión
1. **Orquestación en Sales** (`CancelOrder` ampliado y nuevo `ReturnOrder`), bajo un solo `transaction.atomic` de la vista y bloqueo `for_update` del pedido (patrón existente). Orden: pedido → (bloqueo de empresa si Costeo) → inventario.
2. **Estado nuevo `RETURNED`** en `OrderStatus`, alcanzado solo por `Order.register_return(reason, actor, now)` desde `DELIVERED` (transición `return`). El estado más el `for_update` hacen que un reintento o una solicitud concurrente falle con `invalid_transition` sin reejecutar efectos; los efectos externos además son idempotentes por origen.
3. **Registro de la anulación**: nuevos campos del agregado/modelo `cancelled_by`/`cancelled_by_name`, `returned_at`, `returned_by`/`returned_by_name`, `return_reason`, `refund_acknowledged` (booleano). Migración nueva (no se edita ninguna). No se crea tabla aparte: es una sola anulación por pedido.
4. **Devolución total**: reversa de todo lo existente del pedido, en este orden: (a) `inventory_services.reverse_source_movements('sales_order', order.id)` (reingresa al almacén de origen); (b) Costeo: nuevo `costing_services.reverse_output_cost` con contra-evento al costo registrado al vender, sin cambiar el promedio (como `reverse_receipt_cost`); (c) asientos con `reverse_automatic_entry` en orden inverso: `INVENTORY_SALE_COST`, `SALE_DELIVERY`, y si hay reembolso `SALE_PAYMENT` y `SALE_ADVANCE` por cada cobro (`origin_id = payment.id`) y `reverse_entry` para cobros del libro anterior. Fecha de reverso = hoy; el motor exige período abierto.
5. **Cancelar**: antes de entregar no hay salida ni costo; se revierte `SALE_RECOGNITION` si existe y, si hay cobros contabilizados, `SALE_ADVANCE`/`SALE_PAYMENT`/libro anterior. Con cobros se exige `refund_acknowledged=true` (la persona confirma el reembolso externo); sin él, 409 `refund_acknowledgement_required`.
6. **Reembolso**: no es un movimiento de dinero del sistema; es el contrasiento del cobro. Si hay cobros, `payment_status` pasa a `REFUNDED` (derivado de `refund_acknowledged`).
7. **Reportes**: «pedido válido» excluye también `RETURNED` (`read_queries.valid_orders`).
8. **Vista previa** solo lectura (`GET …/return-preview/`) que enumera salidas, asientos y cobros que se contrarrestarían, sin escribir.
9. **Vínculos para el detalle**: Sales los resuelve leyendo, vía fachadas, movimientos por origen (`list_movements_for_source`) y asientos por evento/origen (`automatic_entries_for`), sin guardar ids.

## Alternativas consideradas
- Nuevo evento contable `SALE_REFUND`: rechazado, el contrasiento con cuentas originales ya cumple el AC y evita configuración.
- Tabla `OrderReturn` separada: innecesaria para devolución total; se reconsiderará con parciales.
- Reintento idempotente con 200: rechazado por ahora; basta 409 sin duplicar efectos.
- Orquestar desde Inventario/Accounting: invierte la dirección de dependencias.

## Estrategia de rollback / mitigación
Una transacción: cualquier fallo deja todo intacto. Los contrasientos y movimientos son aditivos (el historial se conserva), no hay borrado. Migración solo agrega columnas nulas/por defecto: reversible con la migración inversa; revertir el despliegue deja pedidos `RETURNED` visibles como no válidos para reportes (se corregiría por datos).

## Consecuencias
Sales conoce cuatro fachadas más (ya conocía tres); Costeo suma un tipo de evento (migración); devolución parcial futura requerirá nuevo modelo por línea.
