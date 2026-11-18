# REV-2026-11-18-revertir-asiento-al-anular-gasto-01: EDGE-01 y EDGE-02 sin prueba dedicada en expenses

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-18-revertir-asiento-al-anular-gasto.md (v1)
**Spec reference:** EDGE-01, EDGE-02
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El plan lista EDGE-01 (asiento no encontrado: no se inventa reversión) y EDGE-02 (hoy fuera de todo período fiscal → 409 `date_outside_fiscal_period`). EDGE-01 solo se cubre de forma indirecta con el caso de gasto sin cobertura; EDGE-02 no se prueba en `expenses` (la regla vive en `accounting` y ya está probada allí).

## Expected behavior
Una prueba por edge case del plan en `expenses/tests/test_voiding_api.py`.

## Actual behavior
`test_voiding_api.py` no contiene ningún caso con `date_outside_fiscal_period`.

## Evidence
Informe del Quality Gate (subagente aislado, 2026-11-18): backend 2222 OK, frontend 1664 SUCCESS; ningún AC sin verificación. No bloquea.

## Resolución
Se añadieron `test_a_posted_expense_whose_entry_is_missing_is_voided_without_inventing_a_reversal` (EDGE-01) y `test_voiding_when_today_is_outside_every_period_fails_and_keeps_the_expense_active` (EDGE-02) en `test_voiding_api.py`; `expenses/tests`: OK.
