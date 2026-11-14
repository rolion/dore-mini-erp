# REV-2026-11-14-pagos-servicios-libro-entradas-01: La prueba «dental» usa una proforma de cotizaciones

**Status:** Resolved
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-14-pagos-servicios-libro-entradas.md (v1)
**Spec reference:** AC-02
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
AC-02 exige cubrir proformas `quotation` y `dental`; `test_dental_payment_creates_its_entry` no ejercita `kind='dental'`.

## Expected behavior
Una prueba con `kind='dental'` (patrón en `receivables/tests/test_api.py:206`).

## Actual behavior
Solo se prueba `quotation`; el nombre afirma algo que no se verifica. Riesgo bajo: el adaptador no depende del `kind`.

## Evidence
`backend/modules/receivables/tests/test_payment_ledger.py`, test `test_dental_payment_creates_its_entry`.

## Resolución
Corregido: `test_dental_payment_creates_its_entry` cobra una proforma `dental` real; AC-10 queda en `test_payments_appear_in_the_ledger_api_with_correct_totals`.
