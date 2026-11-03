# REV-2026-10-30-valorar-recepciones-consumos-costo-historico-02: Orden de bloqueo no determinista en recepciones multilínea y sin prueba de concurrencia (EDGE-04)

**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-30-valorar-recepciones-consumos-costo-historico.md (v1)
**Spec reference:** EDGE-04, NFR («bloqueo almacén + fila de costo, orden por product_id»), Test Specification (concurrencia con dos almacenes)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El plan exige bloquear las filas de costo en orden por `product_id`. `RecordOutputs` ordena (`sorted(pending, key=product_id)`), pero la recepción (`RegisterReception._enter_stock` → `StockEntryAdapter.register_entries`) registra una entrada por línea en el orden de las líneas, cada una con `lock_state` (select_for_update de la fila de costo) dentro de la misma transacción externa. Además, `ConfirmAdjustment`/`RecordMovement` bloquean primero el almacén y luego el producto.

## Expected behavior
Orden de adquisición de bloqueos determinista (por product_id) para evitar interbloqueos entre almacenes distintos, y una prueba que demuestre la serialización de dos almacenes sobre el mismo producto (planificada en el plan y declarada como deuda en el TASK).

## Actual behavior
Dos recepciones en almacenes distintos con los mismos productos en orden inverso (X,Y vs Y,X) pueden tomar las filas de costo en orden cruzado y provocar un interbloqueo de PostgreSQL (una transacción abortada, 500). No hay prueba de concurrencia; la mitigación declarada del riesgo principal del TASK («carrera entre almacenes») no está verificada. Probabilidad baja, impacto: operación fallida y reintento.

## Evidence
backend/modules/purchases/infrastructure/adapters.py (loop `for product_id, quantity in lines` sin ordenar); backend/modules/purchases/application/receipt_commands.py (`entries` en orden de líneas); backend/modules/inventory/application/movement_use_cases.py:146 (único `sorted`). `grep -n "concurr\|Thread\|TransactionTestCase" backend/modules/costing/tests/test_movement_valuation.py` no encuentra ninguna prueba de concurrencia. Reconocido como deuda en TASK «Deuda técnica».
