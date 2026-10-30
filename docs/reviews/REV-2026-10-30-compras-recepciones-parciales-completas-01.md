# REV-2026-10-30-compras-recepciones-parciales-completas-01: La prueba de concurrencia no se omite fuera de PostgreSQL

**Status:** Fixed
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-30-compras-recepciones-parciales-completas.md (v1)
**Spec reference:** Test Specification → Integration tests ("`test_receipt_concurrency.py` (BD, PostgreSQL real en publish; `skipUnless` como la de compras)"); AC-17
**Plan mode:** COMPLETO
**Suggested owner:** delivery-engineer

## Description
El PLAN exige que la prueba de concurrencia lleve `skipUnless` (solo PostgreSQL, donde `select_for_update` bloquea de verdad). La clase `ReceiptRowLockTests` no tiene ningún decorador de omisión.

## Expected behavior
Con un motor sin bloqueo de fila real la prueba se omite con un motivo explícito (como `sales/tests/test_delivery_inventory.py:356`: `@skipUnless(connection.vendor == 'postgresql', ...)`), en vez de fallar o dar un falso resultado.

## Actual behavior
La prueba corre siempre. Con PostgreSQL (el motor del proyecto) no hay impacto; con cualquier otro motor `select_for_update` es un no-op y la aserción `len(failures) == 1` no se sostiene (falso negativo de la prueba, no del código).

## Evidence
- `backend/modules/purchases/tests/test_receipt_concurrency.py:26`: `class ReceiptRowLockTests(TransactionTestCase):` sin decorador; el archivo no importa `skipUnless`.
- Referencia del patrón: `backend/modules/sales/tests/test_delivery_inventory.py:356`: `@skipUnless(connection.vendor == 'postgresql', 'La concurrencia real exige PostgreSQL (select_for_update).')`.
- La prueba no pudo ejecutarse en esta revisión (sin credenciales de PostgreSQL); AC-17 queda NO VERIFICADO en ejecución.
