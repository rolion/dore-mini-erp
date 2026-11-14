# REV-2026-11-14-pagos-ventas-libro-entradas-01: Aserciones débiles y ramas sin prueba en test_payment_ledger.py

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-14-pagos-ventas-libro-entradas.md (v1)
**Spec reference:** AC-10, AC-07, AC-03, EDGE-01, EDGE-04
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Algunas pruebas no ejercitan realmente lo que su comentario afirma, y hay ramas nuevas sin cobertura.

## Expected behavior
Cada AC/EDGE tiene una prueba que falla si la regla se rompe.

## Actual behavior
- `test_other_company_data_is_never_used` (AC-10): las dos últimas aserciones solo comprueban que la empresa B crea un pedido `NEW`; el comentario dice que "su propio cobro se rechaza" pero no se ejecuta ningún cobro de B. "Cuenta ajena imposible" no se prueba.
- AC-10 "registrar un cobro no exige acceso a pantallas contables" no tiene prueba con un usuario sin permisos contables.
- `EntryConflict` -> 409 `ledger_conflict` (AC-07) no tiene prueba; solo `EntryValidationError` y `RuntimeError`.
- EDGE-01 se prueba solo con pedido saldado, no cancelado; EDGE-04 (pedido cancelado + clave nueva -> 409 `order_cancelled` sin entrada) no tiene prueba.
- AC-03 no cubre `deliver` ni "agregar ítems" con accounting habilitado.

## Evidence
`backend/modules/sales/tests/test_payment_ledger.py` líneas 173-185 (`test_other_company_data_is_never_used`), 137-152 (solo dos tipos de fallo del libro), 94-103 (replay solo sobre saldado). Búsqueda de `ledger_conflict`, `order_cancelled` en ese archivo: sin resultados.

## Resolución
Resuelto: se fortaleció `test_other_company_data_is_never_used` (cobro de B rechazado sin su mapeo y luego con su propia cuenta, sin tocar la de A) y se añadieron `test_ledger_conflict_is_a_409_and_persists_nothing`, `test_cancelled_order_rejects_new_key_but_replays_the_old_one` (EDGE-01/04) y `test_adding_items_and_delivering_create_no_entries` (AC-03). Nota: el sistema no tiene un permiso contable separado (todo cobro exige solo el permiso de Ventas), así que no hay un usuario «sin permisos contables» que probar.
