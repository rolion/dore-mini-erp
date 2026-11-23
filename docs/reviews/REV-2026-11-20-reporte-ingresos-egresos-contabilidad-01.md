# REV-2026-11-20-reporte-ingresos-egresos-contabilidad-01: Línea nueva de 124 caracteres (E501)

**Status:** Fixed
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-20-reporte-ingresos-egresos-contabilidad.md (v1)
**Spec reference:** N/A (CLAUDE.md: cero avisos de lint en lo cambiado)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El docstring de `DjangoJournalRepository.result_by_month` superaba los 120 caracteres.
## Expected behavior
flake8 sin avisos en lo cambiado.
## Actual behavior
`repositories.py:609:121: E501 line too long (124 > 120 characters)`.
## Evidence
Salida de flake8 del Quality Gate. Corregido acortando el docstring; flake8 ya no avisa en esas líneas.
