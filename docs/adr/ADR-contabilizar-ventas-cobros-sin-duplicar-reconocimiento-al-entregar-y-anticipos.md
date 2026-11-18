# ADR-contabilizar-ventas-cobros-sin-duplicar-reconocimiento-al-entregar-y-anticipos: Reconocimiento al entregar y cobros previos como anticipos de clientes

**Estado:** Propuesto
**Task relacionado:** TASK-contabilizar-ventas-cobros-sin-duplicar
**Fecha:** 2026-11-17
**Reemplaza parcialmente a:** `ADR-contabilizar-ventas-cobros-sin-duplicar-puerto-reconocimiento-y-cobro.md` (decisiones 2, 3, 5 y 6 y la nota 2b; el resto sigue vigente). Ese ADR no se borra.

## Contexto
La primera versión reconocía el ingreso al confirmar el pedido (NUEVO → EN PREPARACIÓN) y todo cobro iba contra Cuentas por cobrar. La persona cambia la regla (2026-11-17): el ingreso se reconoce **al entregar** (LISTO → ENTREGADO) y los cobros hechos antes de entregar son **anticipos de clientes** (Pasivo). Confirmar y marcar listo ya no contabilizan. Hay pedidos que ya fueron reconocidos al confirmar con la lógica anterior, y pedidos con cobros hechos fuera de cobertura que se entregan dentro de ella: la transición debe distinguirlos sin duplicar ingresos ni dejar contabilidad incompleta.

## Decisión
1. **Catálogo de Contabilidad (CONT-12) ampliado, aditivo:**
   - Rol nuevo `CUSTOMER_ADVANCES` «Anticipos de clientes», clasificación **Pasivo**, un mapeo por empresa en `accounting_posting_account` (sin migración; sin códigos ni IDs fijos).
   - Evento `SALE_ADVANCE` (Debe cuenta de dinero del método / Haber Anticipos de clientes).
   - Evento `SALE_DELIVERY` (≤ 30 caracteres): Debe Anticipos de clientes (anticipos aplicados) + Debe Cuentas por cobrar (saldo) / Haber Ingresos por ventas (total). Es el primer evento con **dos líneas de Debe**: `Event` gana `extra_debit_role` opcional; la línea de importe cero **no se genera**.
   - `SALE_RECOGNITION` queda en el catálogo solo como **evento histórico** (`active=False`): no se muestra en el panel ni se usa para nuevos pedidos, pero sigue reconocido para cobrar y revertir pedidos que ya tienen ese asiento.
   - `SALE_PAYMENT` se conserva (Debe método / Haber Cuentas por cobrar) para cobros de pedidos ya reconocidos.
2. **Fachada aditiva:** `post_automatic_entry(..., advance_applied=None)` — solo válido para eventos con `extra_debit_role`: la línea extra lleva `advance_applied`, la principal `amount − advance_applied`, el Haber `amount`; ninguna línea de importe 0. Y `automatic_entry_origins(company_id, event, origin_ids) -> set[UUID]` (una consulta) para saber qué cobros ya tienen asiento. Misma idempotencia por `(empresa, evento, origin_id)`.
3. **Estado contable del pedido** (puerto `SalesPosting.recognition_state(order_id)`): `AT_CONFIRM` si existe `SALE_RECOGNITION` (lógica anterior), `AT_DELIVERY` si existe `SALE_DELIVERY`, `None` en otro caso. Se lee del libro (única fuente de verdad); sin bandera ni migración en Ventas.
4. **Confirmar y marcar listo no contabilizan** ni exigen configuración. Se eliminan el reconocimiento al confirmar y la regla `order_has_prior_payments` de ese paso.
5. **Camino de cada cobro** (con Contabilidad habilitada; cada cobro un solo camino):
   | Condición | Camino |
   |---|---|
   | Estado `AT_CONFIRM` o `AT_DELIVERY` | `SALE_PAYMENT` (Debe método / Haber CxC). Fecha sin cobertura → 409 `payment_date_not_covered` |
   | Sin reconocer, estado NUEVO | con cobertura hoy: 409 `order_not_confirmed`; sin cobertura: libro anterior (como antes) |
   | Sin reconocer, EN PREPARACIÓN o LISTO | con cobertura hoy: `SALE_ADVANCE` (fecha del cobro sin cobertura → 409 `payment_date_not_covered`); sin cobertura hoy: libro anterior |
   | Sin reconocer, ENTREGADO (entregado sin asiento: antes de la cobertura) | libro anterior, como antes (pedido histórico) |
6. **Entrega** (`DeliverOrder`, misma transacción que la salida de inventario y el cambio de estado; ya bloquea la fila del pedido):
   - Estado `AT_CONFIRM`: no se vuelve a reconocer (sin asiento nuevo).
   - Con cobertura de la fecha de entrega efectiva: se calculan los **anticipos aplicados** = Σ de los cobros del pedido que tienen asiento `SALE_ADVANCE`. Si algún cobro **no tiene** asiento de anticipo (cobros hechos sin cobertura), 409 `order_has_unposted_payments`: no se genera contabilidad incompleta. Si no, `post_automatic_entry(SALE_DELIVERY, origin_id = id del pedido, fecha = fecha de entrega, importe = total con descuento, advance_applied = Σ anticipos)`. Total 0: sin asiento.
   - Sin cobertura de la fecha de entrega: si el pedido ya tiene anticipos contabilizados, 409 `delivery_date_not_covered` (se aplicarían a una entrega sin asiento); si no, se entrega sin asiento como antes.
   - La fecha contable es la **fecha de entrega efectiva** del pedido (`delivered_date`); el período debe estar abierto.
7. **Total estable:** se conserva el bloqueo de productos, cantidades y descuento (409 `order_total_locked`) cuando el pedido está confirmado (estado ≠ NUEVO) y Contabilidad cubre hoy, o ya está reconocido (`AT_CONFIRM`). Sin cobertura, como antes.
8. **Cancelar:** `AT_CONFIRM` sin cobros → reversión del reconocimiento con las cuentas originales; con cobros → 409 `order_has_payments_posted`. Sin reconocer: con algún cobro con asiento `SALE_ADVANCE` → 409 `order_has_payments_posted`; sin cobros (o con cobros fuera de cobertura, como hoy) → se cancela **sin asiento**. Los pedidos entregados siguen sin poderse cancelar.
9. **Vínculos y trazabilidad:** el asiento de anticipo guarda `origin_id` = id del **pago** y la descripción nombra el pedido; el de entrega, `origin_id` = id del **pedido**; la aplicación del anticipo queda en las líneas del asiento de entrega y es única (un asiento por pedido), de modo que repetir o competir no la aplica dos veces.
10. **Sin Contabilidad o sin cobertura:** sin cambios (libro anterior o nada); deshabilitar Contabilidad deja a Ventas independiente (consecuencia aceptada, ver decisión 10 del ADR anterior).

## Alternativas consideradas
- **Tabla/bandera en Ventas con los anticipos aplicados:** requeriría migración y duplicaría el libro; el estado se deduce de los asientos existentes.
- **Asiento por cada anticipo aplicado:** más asientos sin ganancia; uno por pedido es suficiente y atómico.
- **Mover Caja/Bancos al entregar:** descartado por la persona (no se vuelve a mover Caja al entregar).
- **Reconocer solo el saldo cuando hay cobros previos sin asiento:** lógica contable nueva sin regla definida; se bloquea y queda como decisión pendiente.
- **Acción «Entregar y cobrar»:** no existe hoy en la interfaz; no se crea en esta tarea (el cobro posterior es una acción separada).

## Estrategia de rollback / mitigación
Sin migraciones. Revertir el despliegue devuelve el reconocimiento al confirmar para pedidos nuevos; los asientos `SALE_ADVANCE`/`SALE_DELIVERY` ya creados siguen siendo válidos y se corrigen por reversión manual desde Contabilidad. Pedidos con reconocimiento anterior no se tocan. Un pedido bloqueado por `order_has_unposted_payments` no se puede entregar con cobertura hasta resolver sus cobros sin asiento (ver «Decisiones pendientes» del TASK).

## Consecuencias
- Contabilidad de Ventas necesita configurar Anticipos de clientes (Pasivo) antes de cobrar por adelantado, y Cuentas por cobrar e Ingresos antes de entregar.
- Primer evento de tres líneas del catálogo; el panel de configuración muestra su asiento previsto.
- Pedidos cobrados antes de la cobertura y entregados con cobertura quedan bloqueados hasta decidir su tratamiento.
- Los pedidos confirmados con la lógica anterior conviven con los nuevos; se distinguen por su asiento, no por una fecha.
