# REV-2026-10-27-inventario-stock-almacenes-unidades-03: Tests dependientes de la resolución del reloj son intermitentes

**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-27-inventario-stock-almacenes-unidades.md (v1)
**Spec reference:** N/A (preexistente)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Tests dependientes de la resolución del reloj son intermitentes.

## Expected behavior
Tests deterministas.

## Actual behavior
`sales...test_item_order_is_preserved`, `catalog...test_patch_updates_fields_and_refreshes_updated_at` y `modularity...test_changes_are_recorded_with_user_and_values` fallan a veces en Windows (marcas de tiempo iguales / orden por UUID); pasan al repetir. Ninguno está en el diff.

## Evidence
Corridas repetidas del mismo código: fallos distintos en cada una y OK en otras.

## Resolution
No atribuible al task; se informa como limitación conocida.
