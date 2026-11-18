# REV-2026-11-15-incorporar-egresos-reversion-libro-02: Invariantes INV-03/INV-05 solo en dominio y fachada, no en base de datos

**Status:** Open (no bloqueante)
**Severity:** Low
**Category:** ARCHITECTURE
**Related plan:** docs/plans/PLAN-2026-11-15-incorporar-egresos-reversion-libro.md (v1)
**Spec reference:** INV-03, INV-05
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
La base no impide un egreso sin `classification_id` ni una reversión con la misma dirección que su original; toda escritura real pasa por `record_entry`/`reverse_entry`.

## Expected behavior
Opcional: defensa en profundidad con CheckConstraints.

## Actual behavior
Ver descripción.

## Evidence
`models.py` solo tiene `accounting_entry_reversal_link` y la unicidad.
