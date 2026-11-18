# ADR-contabilizar-inventario-costo-ventas-ledger-de-costo-y-salida-valorizada: Ledger de costo en Costeo y salida valorizada

**Estado:** Propuesto
**Task relacionado:** TASK-contabilizar-inventario-costo-ventas
**Fecha:** 2026-11-17

## Contexto
Hay evento y roles contables para el costo de ventas (CONT-12) pero no existe costo corriente: Costeo solo conserva la valoración inicial y las recepciones no llevan valor. La persona decidió usar promedio móvil ponderado y dejar los ajustes fuera. Hay que asentar el costo de cada salida por venta de forma atómica con el stock y sin duplicar el asiento de recepción de COM-02.

## Decisión
1. **Ledger de costo en `costing`** (tabla nueva `costing_cost_event`, migración `0002`, solo `CreateModel`): evento inmutable por `(empresa, tipo OUT|IN|IN_REVERSAL, source_type, source_id, product_id)` con `quantity`, `unit_cost` (6 dec.), `total_cost` (2 dec., `ROUND_HALF_UP`), `average_after` (6 dec.), vínculo `reverses_id` y `occurred_at`. Único por `(empresa, tipo, source_type, source_id, product_id)` → idempotencia. Sin FK a productos de otros módulos.
2. **Promedio móvil:** el costo vigente de un producto es `average_after` de su último evento IN, o el `unit_cost` de la valoración inicial si no hay eventos. Recepción: `new_avg = (saldo_previo × avg + qty × costo_recepción) / (saldo_previo + qty)` (saldo previo > 0 y avg conocido; si no, `new_avg = costo_recepción`), redondeo `ROUND_HALF_UP` a 6 decimales. Las salidas **no** cambian el promedio. Una reversión de recepción registra un evento IN_REVERSAL al costo original y deja el promedio sin cambios.
3. **Fachada `costing.services`:** `cost_receipt(company_id, receipt_id, lines[(product, qty, unit_cost, saldo_previo)], …)`, `reverse_receipt_cost(...)`, `cost_outputs(company_id, source_type, source_id, lines)` → `CostedOutput` con costo por línea y total; idempotente (reintento devuelve lo registrado). Todo bajo `inventory.services.lock_company_stock`. Sin costo para un producto (Costeo deshabilitado, sin adopción o sin promedio) lanza `CostUnavailable` con la lista de productos.
4. **Salida valorizada y asiento (dueño: Ventas, en la transacción de `DeliverOrder`):** tras `register_outputs`, si el módulo Contabilidad cubre la fecha de entrega y hay productos controlados, el adaptador de Ventas llama `costing.cost_outputs` y `accounting.post_automatic_entry('INVENTORY_SALE_COST', order.id, fecha de entrega, importe = Σ costo de líneas)`. Antes verifica `check_posting_ready`; cualquier falla (configuración, costo, período) revierte stock, costo y entrega (misma transacción). Reintento: idempotente por `(INVENTORY_SALE_COST, order.id)`. Importe total 0 (costo cero declarado) → se registra el costo pero no se genera asiento. Sin cobertura contable el ledger de costo igual se actualiza si Costeo está habilitado, sin asiento ni bloqueo.
5. **Recepción (coordinación con COM-02):** el **único dueño del asiento de recepción es COM-02** (`PURCHASE_RECOGNITION`, Debe Inventario/Haber CxP). INV-01 **no** registra asiento al recibir; solo traslada el costo (`unit_price` de la línea) al ledger. Así un ingreso nunca produce dos asientos. Sin Costeo adoptado la recepción sigue como hoy.
6. **Ajustes y devoluciones:** los ajustes de inventario quedan sin asiento (decisión de la persona; límite documentado). No existe devolución de ventas, por lo que no se construye reversión de salidas; el ledger y `reverse_automatic_entry` quedan listos. Lo que hoy se revierte (recepciones) conserva el costo original por el evento IN_REVERSAL.
7. **Dependencias:** `sales → costing` y `purchases → costing` solo por `costing.services` (opcionales por módulo habilitado); `costing → inventory` ya existe. Sin importar infraestructura ajena ni `accounts`.

## Alternativas consideradas
- **Costo en `StockMovement`:** altera un libro inmutable de otro módulo; ya descartado en el ADR de Costeo.
- **Que Inventario asiente la salida (evento del módulo `inventory`):** obligaría a Inventario a conocer la entrega y duplicaría la orquestación; Ventas ya es quien tiene la transacción y la fecha.
- **Costo estático de la adopción:** deja el costo desactualizado tras comprar (descartada por la persona).
- **Asentar la recepción en INV-01:** duplicaría COM-02 (descartada).
- **PEPS/UEPS o costo por almacén:** fuera de alcance; el método declarado es el promedio.

## Estrategia de rollback / mitigación
La migración solo crea una tabla (reversible con `migrate costing 0001`); no cambia datos existentes. Los cambios de Ventas/Compras son aditivos y condicionales a Costeo/Contabilidad habilitados, por lo que revertir el PR vuelve al comportamiento actual. Un error de costo no se edita: se corrige con un evento posterior y la reversa del asiento con `reverse_automatic_entry`.

## Consecuencias
- Nace el costo corriente y el asiento de costo de ventas; con Contabilidad cubierta, entregar productos con stock exige Costeo adoptado (bloqueo explícito si falta).
- Limitaciones: ajustes sin valor ni asiento; unidades sin costo previo se promedian al costo de la primera recepción; sin devolución de ventas; sin vista de costo promedio.
- Compras queda acoplada a `costing` por una llamada por recepción.
