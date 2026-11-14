# REV-2026-11-13-crear-cuentas-mapear-metodos-pago-01: Sin test que fije el contrato del gate de accounting

**Status:** Resolved
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-13-crear-cuentas-mapear-metodos-pago.md (v1)
**Spec reference:** Test Specification (integración, gate)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Las vistas de configuración declaran `required_modules = ()` (intencional) pero ningún test en `modularity/tests/test_enforcement.py` fija que la configuración funciona con `accounting` deshabilitado.

## Expected behavior
Un test que confirme 200 en `/api/accounting/accounts/` y `/payment-methods/` con el módulo deshabilitado.

## Actual behavior
Ver descripción.

## Evidence
`grep accounting backend/modules/modularity/tests/test_enforcement.py` sin resultados.

## Resolution (2026-11-13)
Tests `ConfigurationContractTests` (configuración con el módulo deshabilitado).
