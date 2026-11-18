# REV-2026-11-16-periodos-fiscales-por-empresa-05: Desviaciones menores no declaradas

**Status:** Resolved
**Severity:** Low
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-11-16-periodos-fiscales-por-empresa.md (v1)
**Spec reference:** N/A
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El puerto PeriodUsage quedó en application/fiscal_periods.py (no ports.py) y la excepción se llama FiscalPeriodContractError (no PeriodContractError).

## Expected behavior
Declararlo en el TASK.

## Actual behavior
Ver descripción.

## Evidence
Quality Gate (subagente aislado), TASK ## Implementación. Backend 1678 OK; frontend 1430 OK (2 de 3 corridas, ver nota del flake preexistente `screens-i18n.spec.ts:58-65`, ajeno al diff).
