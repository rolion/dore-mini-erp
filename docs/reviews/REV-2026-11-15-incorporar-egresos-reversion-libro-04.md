# REV-2026-11-15-incorporar-egresos-reversion-libro-04: Falta test explícito de moneda distinta de la cuenta en egresos

**Status:** Open (no bloqueante)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-15-incorporar-egresos-reversion-libro.md (v1)
**Spec reference:** EDGE-02
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El código valida la moneda (`services.py`), pero `test_entry_expenses.py` no tiene un caso dedicado para egresos (puede estar cubierto por pruebas previas de `record_entry` de ingresos).

## Expected behavior
Un test de egreso con moneda distinta de la cuenta.

## Actual behavior
Ver descripción.

## Evidence
Sin caso en `test_entry_expenses.py`.
