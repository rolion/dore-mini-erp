# REV-2026-11-26-reporte-balance-general-contabilidad-01: Las pruebas de API no pueden pasar

**Status:** Fixed
**Severity:** High
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-26-reporte-balance-general-contabilidad.md (v1)
**Spec reference:** AC-01, AC-02, AC-03, AC-05, AC-07, INV-05
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`test_balance_sheet_api.py`: (a) no crea período fiscal y `post_journal_entry` exige uno abierto (`services.py:346-348`, `DateOutsideFiscalPeriod`); (b) la prueba de cuentas sin clasificar publica un asiento contra una cuenta sin clase, que `usable_currency` rechaza (`application/journal.py:51-52`).

## Expected behavior
Pruebas de API que ejerciten AC-01..AC-07.

## Actual behavior
Al menos 5 de 7 pruebas fallarían por el entorno de prueba, no por el código de producción.

## Evidence
Inspección del Quality Gate (sin PostgreSQL local). Referencia correcta: `test_income_expense_api.py:23` crea el período con `make_period`.

## Resolución
`make_period` para ambas empresas en `setUp`; el caso sin clasificar publica con la cuenta clasificada y la desclasifica por ORM. Siguen sin ejecutarse (sin PostgreSQL).
