# REV-2026-11-15-incorporar-egresos-reversion-libro-03: Rollback de la migración 0006 con filas nuevas

**Status:** Open (no bloqueante)
**Severity:** Low
**Category:** ARCHITECTURE
**Related plan:** docs/plans/PLAN-2026-11-15-incorporar-egresos-reversion-libro.md (v1)
**Spec reference:** ADR, estrategia de rollback
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
`migrate accounting 0005` falla si ya existen filas EXPENSE/REVERSAL que violen la unicidad antigua. Riesgo aceptado y documentado en el ADR (revertir antes de que GAS-01/COM-01 escriban); no se ejecutó la inversa.

## Expected behavior
Rollback documentado.

## Actual behavior
Ver descripción.

## Evidence
Revisión estática de `0006_entry_direction_operation_reversal.py`.
