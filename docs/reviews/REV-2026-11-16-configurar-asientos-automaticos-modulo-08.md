# REV-2026-11-16-configurar-asientos-automaticos-modulo-08: flake8 reporta E303 en la prueba añadida para REV-02

**Status:** Resolved
**Severity:** Low
**Category:** CODE_QUALITY
**Related plan:** docs/plans/PLAN-2026-11-16-configurar-asientos-automaticos-modulo.md (v1)
**Spec reference:** REV-04 (limpieza de flake8)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El commit de corrección (4870948) cerró REV-04 pero introdujo un nuevo aviso de estilo.

## Expected behavior
Los archivos nuevos o modificados de `backend/modules/accounting` pasan `flake8 --max-line-length=120` sin avisos nuevos.

## Actual behavior
`modules/accounting/tests/test_posting_service.py:120:5: E303 too many blank lines (2)`: el método `test_a_date_inside_a_gap_between_two_coverage_periods_is_not_posted` tiene dos líneas en blanco antes dentro de la clase `CoverageTests`. El resto de avisos (E501 en use_cases.py:135/245, models.py, repositories.py, services.py:158, test_entry_service.py; E128 en test_unified_journey.py:76) son preexistentes; E501 en `migrations/0011_posting_account.py:23,27` es código autogenerado de la migración de esta tarea.

## Evidence
`python -m flake8 --max-line-length=120 <19 archivos .py del diff>` → FLAKE=1 con la lista anterior. bandit sobre domain/posting.py, application/, api/ y services.py: sin hallazgos (exit 0).

## Resolution
Línea en blanco sobrante eliminada; flake8 sin avisos nuevos en las pruebas de posting.
