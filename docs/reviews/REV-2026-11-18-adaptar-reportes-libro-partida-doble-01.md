# REV-2026-11-18-adaptar-reportes-libro-partida-doble-01: El reporte no excluye el libro anterior al corte y ninguna prueba lo verifica

**Status:** Fixed (pendiente de re-verificación)
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-18-adaptar-reportes-libro-partida-doble.md (v1)
**Spec reference:** INV-R5, AC-05
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
INV-R5 y AC-05 exigen que el libro anterior al corte no se sume (`partial=true` con `cutoffDate` y sin sumar lo anterior). La implementación solo calcula `partial`; no filtra por corte.

## Expected behavior
Los asientos con fecha contable anterior a `cutoff_date` no entran en flujo, saldo inicial ni resultado, o bien se demuestra con una prueba que el libro nunca los contiene.

## Actual behavior
`DjangoJournalRepository.money_lines` y `movements_by_account` filtran solo por company_id y fecha contable, sin considerar el corte. `post_journal_entry`/`ReverseJournalEntry` no validan el corte (sin referencias a cutoff en `application/journal.py`), así que un asiento manual anterior al corte sí se sumaría. `LedgerReportTests.test_coverage_is_reported_by_cutoff` solo comprueba el indicador `partial`/`cutoff_date` con un rango sin asientos; no hay prueba de «sin sumar lo anterior». Esta verificación no se pudo ejecutar (BD).

## Evidence
- backend/modules/accounting/infrastructure/django/repositories.py:588-609 (sin filtro de corte)
- backend/modules/accounting/tests/test_ledger_report.py: test_coverage_is_reported_by_cutoff
- grep 'cutoff' en backend/modules/accounting/application/journal.py: sin coincidencias

## Resolución
Corregido en el código (corte aplicado con `since` en `movements_by_account` y `money_lines`, más `test_entries_before_the_cutoff_are_not_summed`); la prueba con BD sigue sin ejecutarse.
