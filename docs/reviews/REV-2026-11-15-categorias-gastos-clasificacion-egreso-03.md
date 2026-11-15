# REV-2026-11-15-categorias-gastos-clasificacion-egreso-03: Textos de error de la pestaña acoplados a claves de Clientes

**Status:** Resolved (pendiente de re-verificación por el Quality Gate)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-15-categorias-gastos-clasificacion-egreso.md (v1)
**Spec reference:** N/A (consistencia i18n)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Los errores de red/genéricos usan claves `CUSTOMERS.CUSTOMERS_API_SERVICE.*`.

## Expected behavior
Claves propias o de `COMMON`.

## Actual behavior
Funciona y pasa i18n:check, pero acopla textos entre features.

## Evidence
expense-config-api.service.ts (toError).
