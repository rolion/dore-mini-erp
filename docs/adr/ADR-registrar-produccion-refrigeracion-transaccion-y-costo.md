# ADR-registrar-produccion-refrigeracion-transaccion-y-costo: Pasar a refrigeración como una sola transacción con costo

**Estado:** Propuesto
**Task relacionado:** TASK-registrar-produccion-refrigeracion
**Fecha:** 2026-11-26

## Contexto
DORE-PROD-004 exige que consumo de ingredientes, entrada del granel con lote y cambio de estado ocurran juntos, sin duplicar con reintentos, y que el lote conserve el costo de lo consumido. Inventario ya ofrece `record_outputs`, `create_lot` y `lock_company_stock`; Costeo ofrece `cost_outputs` y `cost_receipt`. Producción solo guardaba la orden.

## Decisión
1. **Caso de uso `RefrigerateOrder` en Producción**, dentro de un único `transaction.atomic` y con la orden bloqueada (`for_update`). Orden de pasos: (a) validar estado `IN_PREPARATION` y datos (consumos ≥ 0, rendimiento > 0, `entered_at` ≥ `started_at` y no futura); (b) `inventory.record_outputs` (salidas de ingredientes con consumo > 0; `source_type='production_order'`, `source_id=<orden>`; todas o ninguna); (c) `costing.cost_outputs` de esas salidas → costo total consumido; (d) `inventory.create_lot` del producto resultante (cantidad real, `source_id=<orden>`, `occurred_at=entered_at`); (e) `costing.cost_receipt` del resultado con costo unitario = costo total / cantidad elaborada; (f) `order.refrigerate(...)` guarda consumos reales, rendimiento real, lote (id y código), fecha de ingreso y costo. Cualquier excepción revierte todo.
2. **Faltantes:** `InsufficientStock` se traduce a 409 `insufficient_stock` con la lista `shortages` (producto, requerido, disponible, faltante) y la orden no cambia. La política de stock negativo de la empresa sigue mandando (Inventario es la única fuente de esa regla).
3. **Idempotencia:** la orden bloqueada cambia de estado una sola vez; un reintento sobre una orden ya `REFRIGERATING` responde 409 `order_state` sin escribir. Además `record_outputs`/`create_lot`/`cost_*` son idempotentes por `(production_order, id de la orden)`, de modo que un fallo parcial previo nunca duplica.
4. **Costo:** se aplica solo si Costeo está habilitado y la empresa adoptó la valoración (`costing.is_valued`); si `cost_outputs` lanza `CostUnavailable` por falta de promedio de algún insumo, la operación **no** se bloquea: el lote ingresa y la orden guarda `cost_total = null` (sin costo). Con costo, el promedio del producto resultante se actualiza por `cost_receipt` y el costo total consumido queda en la orden. No se genera asiento contable (fuera de alcance; Costeo no lo hace).
5. **Modelo:** el agregado suma estado `REFRIGERATING`, `actual_yield`, `entered_at`, `refrigerated_at`, `lot_id`, `lot_code`, `cost_total` y, por ingrediente, `actual_quantity`. Migración `production/0003` aditiva (columnas nulas) con restricción de coherencia estado↔campos. El lote se guarda por id y código (sin FK entre módulos).
6. **Dependencias:** `production → costing` permitido solo por `costing.services` (se agrega a `ALLOWED_DEPENDENCIES`); Costeo sigue siendo opcional (`module_gate`), no se agrega a `requires`.
7. **Reversión desde Inventario:** `production_order` se agrega a `_BLOCKED_SOURCES` (`reverse_from_origin`): los movimientos de una orden no se revierten a mano; deshacer producción es una tarjeta futura de Producción.

## Alternativas consideradas
- **Orquestar desde Inventario:** acopla Inventario con recetas; descartada.
- **Costo obligatorio (bloquear sin valoración):** impide producir en empresas sin Costeo; descartada, se registra «sin costo».
- **Movimientos sin `record_outputs` (uno por uno):** pierde el «todas o ninguna» y la lista completa de faltantes; descartada.
- **Reintento por clave del cliente:** innecesaria, el estado de la orden bloqueada ya es la clave.

## Estrategia de rollback / mitigación
Migración aditiva (columnas nulas y estado nuevo): revertir el código deja columnas sin uso. Toda la operación es atómica, sin estados intermedios. Los lotes y movimientos ya creados no se borran al revertir el código (el libro es de solo inserción); el backup previo al despliegue cubre el resto.

## Consecuencias
Producción depende ahora de Costeo (opcional) y su `test_boundaries` y `ddd.md` se actualizan. Las tarjetas de liberación y empaque (PROD-005/007) parten de `lot_id` en la orden. Un costo ausente queda visible («Sin costo») y no se recalcula después.
