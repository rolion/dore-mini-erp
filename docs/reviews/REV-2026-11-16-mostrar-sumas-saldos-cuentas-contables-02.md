# Falta la prueba de módulo `accounting` deshabilitado / acceso no autenticado en la API de saldos

**Status:** Resolved (53e31d6, verificado en la segunda pasada del Quality Gate)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-16-mostrar-sumas-saldos-cuentas-contables.md (v1)
**Spec reference:** Test Specification › Integration tests («módulo accounting deshabilitado → 403/rechazo»); Authorization / permissions
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El plan exige probar que con el módulo `accounting` deshabilitado la API rechaza la petición. `test_trial_balance_api.py` habilita el módulo en `setUp` y no tiene ningún caso de módulo deshabilitado ni de petición sin autenticar. La vista declara `required_modules = ('accounting',)` (correcto en código), pero la barrera no está cubierta para este endpoint.

## Expected behavior
Una prueba que desactive el módulo y verifique 403 (y 401/403 sin token).

## Actual behavior
No existe; `grep` de `balances` en `modules/accounting/tests` solo encuentra `test_trial_balance_api.py` sin ese caso.

## Evidence
`TEST_DATABASE_NAME=test_cont04_review ... manage.py test modules.accounting --noinput` → `Ran 327 tests in 57.937s  OK`; `test_trial_balance_api.py` contiene 9 tests: balances_by_difference, idle_and_disabled, disabled_keeps_balance, global_totals, reversal, range, period, invalid_filters, other_company; ninguno de módulo deshabilitado.
