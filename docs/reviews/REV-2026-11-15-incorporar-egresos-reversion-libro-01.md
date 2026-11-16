# REV-2026-11-15-incorporar-egresos-reversion-libro-01: ADR desactualizado respecto a la implementación

**Status:** Open (no bloqueante)
**Severity:** Low
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-11-15-incorporar-egresos-reversion-libro.md (v1)
**Spec reference:** ADR punto 5
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El punto 5 del ADR dice que `reverse_entry` bloquea la cuenta y el original; el punto 7 y el código bloquean solo la cuenta.

## Expected behavior
ADR coherente con el código.

## Actual behavior
Ver descripción.

## Evidence
`ADR-...-direccion-operacion-y-reversion.md` punto 5 vs `backend/modules/accounting/services.py` (`get_for_update(original.account_id)`).
