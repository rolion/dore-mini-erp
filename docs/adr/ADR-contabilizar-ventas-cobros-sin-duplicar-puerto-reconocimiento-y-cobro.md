# ADR-contabilizar-ventas-cobros-sin-duplicar-puerto-reconocimiento-y-cobro: Puerto de contabilización de Ventas, reconocimiento al confirmar y cobro sin doble camino

**Estado:** Propuesto
**Task relacionado:** TASK-contabilizar-ventas-cobros-sin-duplicar
**Fecha:** 2026-11-17

## Contexto
CONT-12 dejó la configuración y la fachada (`check_posting_ready`, `post_automatic_entry`, `reverse_automatic_entry`) con los eventos `SALE_RECOGNITION` y `SALE_PAYMENT`. Ventas hoy solo escribe cada cobro en el libro anterior (`PaymentLedgerAdapter`, origen `PRODUCT`). Hay que reconocer la venta una sola vez, contabilizar cada cobro contra Cuentas por cobrar, y no contar nada dos veces, con transacción atómica, idempotencia y sin tocar los controles de saldo y concurrencia de `RegisterPayment`. Decisiones de negocio de la persona: ver TASK › Decisiones resueltas.

## Decisión
1. **Puerto `SalesPosting`** en `sales/application/ports.py` (reemplaza el uso de `PaymentLedger` en los comandos; el libro anterior queda detrás del mismo puerto como camino de respaldo), implementado por `SalesPostingAdapter` en `sales/infrastructure/adapters.py` sobre `accounting.services`. Métodos: `covers(date)` (¿Contabilidad habilitada y con cobertura?), `recognize(order, actor)`, `is_recognized(order_id)`, `record_payment(order_id, payment, actor)`, `reverse_recognition(order, reason, actor)`. Con el módulo deshabilitado o sin cobertura, nada cambia respecto de hoy.
2. **Reconocimiento al confirmar** (`StartOrderPreparation`, ya dentro del `atomic` y con el pedido bloqueado): `check_posting_ready(SALE_RECOGNITION, hoy)` → si `required` y hay faltantes, 409 `posting_configuration_missing` con los `issues`, **antes** de cambiar el estado. Luego `order.start_preparation()` y `post_automatic_entry(SALE_RECOGNITION, origin_id=order.id, fecha=hoy, importe=order.total)`; el importe es el total con descuento (no hay impuestos). Total 0 → no se contabiliza. Sin cobertura (`posted=False`) → no hay asiento y no se exige configuración.
3. **El camino del cobro lo decide la existencia del reconocimiento**, no una bandera nueva: `is_recognized(order_id)` consulta la fachada (función aditiva `find_automatic_entry(company_id, event, origin_id)`, sin migración).
   - Pedido **reconocido** → asiento `SALE_PAYMENT` (Debe cuenta de dinero del método / Haber Cuentas por cobrar), `origin_id` = id del pago, fecha = `payment_date`, importe = monto del pago. **No se escribe en el libro anterior.** Si la fecha del cobro no tiene cobertura (`posted=False`), 409 `payment_date_not_covered` (evita CxC sin saldar).
   - Pedido **no reconocido** y NEW con cobertura de hoy → 409 `order_not_confirmed` («Confirma el pedido antes de cobrarlo»).
   - Pedido **no reconocido** y confirmado antes de la cobertura (o sin cobertura) → comportamiento actual (libro anterior si Contabilidad está habilitada). Así cada cobro sigue exactamente un camino y no se mezclan libros para el mismo importe.
4. **Orden dentro de `RegisterPayment`**: idempotencia (replay, sin cambios) → decidir camino → `Order.register_payment` (validaciones de saldo/estado existentes) → asiento/entrada → `repository.save`. La fila del pedido bloqueada serializa cobros concurrentes: el segundo ve el saldo del primero; el asiento es idempotente por `(empresa, SALE_PAYMENT, id del pago)`. Cualquier excepción (configuración, período cerrado, motor) deshace pedido, pago y asiento: se traduce a `OrderRuleViolation` → 409 `{code, detail}` (con `issues` para configuración faltante).
5. **Total bloqueado mientras esté contabilizado**: `AddOrderItem`, `ChangeOrderItemQuantity`, `RemoveOrderItem` y `ApplyOrderDiscount` consultan `is_recognized(order_id)` y, si es verdadero, responden 409 `order_total_locked`. Datos no monetarios (cliente, notas, fechas) siguen editables. El dominio `Order` no cambia.
6. **Cancelar**: si `is_recognized` → si el pedido tiene cobros, 409 `order_has_payments_posted` (hasta que exista reembolso, fuera de alcance); si no, `reverse_automatic_entry(SALE_RECOGNITION, order.id, hoy, motivo)` con las cuentas originales (aunque estén deshabilitadas), en la misma transacción. Sin reconocimiento: se cancela como hoy.
7. **Entrega** no contabiliza nada (costo/stock = INV-01).
8. **Frontera:** solo `infrastructure/adapters.py` importa `accounting.services` (ya permitido); `accounting` no importa `sales`. Ventas no guarda cuentas ni importes contables.
9. **API:** misma forma de errores 409 `{code, detail}` de Ventas; `posting_configuration_missing` añade `issues:[{code, subject, message}]`. Ningún endpoint nuevo ni campo de petición nuevo.

## Alternativas consideradas
- **Asiento directo Caja/Ingresos para cobros de pedidos sin reconocer** (tarjeta): descartado por la persona; añade un segundo camino al mismo importe y exige reconciliar al confirmar.
- **Reconocer al entregar:** descartado por la persona (los cobros previos serían anticipos, sin cuenta de anticipos).
- **Bandera `accounting_recognized` en el pedido (migración):** más rápido de leer pero duplica la verdad que ya está en el libro; la consulta por origen del motor es la fuente única.
- **Escribir en ambos libros:** descartado por la persona (doble cómputo).
- **Ajustes/contra-asientos al cambiar el total tras reconocer:** introduce lógica contable no pedida; se bloquea el cambio.
- **Reembolsos al cancelar con cobros:** no existen; se bloquea.

## Estrategia de rollback / mitigación
Sin migraciones. Con Contabilidad deshabilitada o sin cobertura nada cambia. Revertir el despliegue devuelve el comportamiento anterior; los asientos ya creados son válidos y se corrigen por reversión desde Contabilidad (los cobros ya contabilizados no se vuelven a escribir en el libro anterior). Empresas con Contabilidad habilitada pero sin cuentas configuradas quedan sin poder confirmar hasta configurarlas; el mensaje indica dónde (Ventas › Configuración › Asientos automáticos).

## Consecuencias
- Con cobertura, confirmar y cobrar exigen la configuración de CONT-12; el rechazo es explícito, nunca silencioso.
- Pedidos reconocidos no admiten cambios de total ni cancelación con cobros: reglas nuevas, solo con cobertura.
- Convivencia temporal: cobros anteriores a la cobertura siguen en el libro anterior; los posteriores en partida doble (consistente con el corte de apertura).
- Reembolsos, anticipos y costo de ventas quedan para tarjetas posteriores.
