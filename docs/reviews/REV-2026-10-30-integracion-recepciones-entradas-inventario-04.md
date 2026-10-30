# REV-2026-10-30-integracion-recepciones-entradas-inventario-04: Prueba de dominio de inmutabilidad de inventory_mode no añadida

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-30-integracion-recepciones-entradas-inventario.md (v1)
**Spec reference:** INV-01; Test Specification (test_receipt_domain.py)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build (backend)

## Description
El plan lista test_receipt_domain.py («Receipt conserva inventory_mode y no lo cambia»); el diff no lo modifica. INV-01 queda cubierto solo por aplicación y repositorio.

## Expected behavior
Prueba de dominio para inventory_mode.

## Actual behavior
Sin prueba en test_receipt_domain.py; además el campo es asignable directamente (receipt.inventory_mode = …) sin método del agregado, lo que no impone la inmutabilidad.

## Resolution
`Receipt.set_inventory_mode()` fija el modo una sola vez (`ReceiptInventoryModeAlreadySet` si se repite) y `RegisterReception` lo usa; nuevas pruebas en `test_receipt_domain.py` (`InventoryModeTests`).

## Evidence
git diff origin/main...HEAD --stat no incluye backend/modules/purchases/tests/test_receipt_domain.py; receipt_commands.py asigna el campo directamente.
