# REV-2026-11-26-crear-iniciar-orden-receta-02: pruebas de AC-04 y AC-05 con aserciones débiles

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-26-crear-iniciar-orden-receta.md (v1)
**Spec reference:** AC-04, AC-05, AC-06, INV-09 (plan: "comparando saldos de Inventario antes y después")
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
1. `test_order_keeps_snapshot_after_recipe_changes` (AC-04) no verifica el estado de la respuesta del `PUT /api/recipes/<id>/`; si esa edición fallara (400), la prueba pasaría sin demostrar que la orden conserva la copia.
2. `test_draft_edit_and_start_do_not_touch_stock` (AC-05/06) comprueba `StockMovementModel.objects.count() == 0`, pero el plan pide comparar saldos de Inventario antes y después.

## Expected behavior
Afirmar `status_code == 200` en la edición de la receta (y que la receta realmente cambió) y comparar saldos/lotes además del conteo de movimientos.

## Actual behavior
Aserciones más débiles que lo especificado; el comportamiento real del código sí cumple (no hay escritura en Inventario: solo se leen almacenes).

## Evidence
`backend/modules/production/tests/test_order_api.py` (líneas de `test_order_keeps_snapshot_after_recipe_changes` y `test_draft_edit_and_start_do_not_touch_stock`).
