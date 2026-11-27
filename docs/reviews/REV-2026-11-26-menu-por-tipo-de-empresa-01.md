# REV-2026-11-26-menu-por-tipo-de-empresa-01: Aviso E501 en lo cambiado

**Status:** Closed
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-26-menu-por-tipo-de-empresa.md (v1)
**Spec reference:** N/A (regla de `CLAUDE.md`: cero avisos de lint en lo cambiado)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
La línea del registro de `Dore` en `backend/modules/data_import/tests/test_api_integration.py:136` superaba los 120 caracteres tras añadir `company_type`.

## Expected behavior
`ruff` y `flake8` sin avisos en lo cambiado.

## Actual behavior
Un aviso E501 en ambos.

## Evidence
`E501 Line too long (143 > 120) --> modules\data_import\tests\test_api_integration.py:136:121`

**Cierre:** diccionario partido en varias líneas. `ruff check` y `flake8` sobre ese archivo: `All checks passed!`; `ruff check` sobre todos los `.py` cambiados (sin migraciones): `All checks passed!`; `python manage.py test modules.data_import`: `Ran 63 tests / OK`. Cambio solo de formato en una prueba, por lo que no se repitió todo el Quality Gate.
