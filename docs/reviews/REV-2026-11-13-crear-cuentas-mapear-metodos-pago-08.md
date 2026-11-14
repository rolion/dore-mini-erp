# REV-2026-11-13-crear-cuentas-mapear-metodos-pago-08: Sin tests directos de INV-09 y EDGE-05 a nivel API

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-13-crear-cuentas-mapear-metodos-pago.md (v1)
**Spec reference:** INV-09, EDGE-05
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
EDGE-05 solo se prueba en dominio; INV-09 (deshabilitar no borra configuración) sin test.

## Expected behavior
Tests de integración para ambos.

## Actual behavior
Ver descripción.

## Evidence
`test_api.py`.

## Resolution (2026-11-13)
Tests `test_disabling_the_module_keeps_the_configuration` (INV-09) y `test_reactivating_a_method_with_an_unusable_account_is_rejected` (EDGE-05, API).
