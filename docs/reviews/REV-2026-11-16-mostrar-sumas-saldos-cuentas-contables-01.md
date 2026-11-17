# Sin pruebas para el selector de período, filtros→URL y «Limpiar filtros» de la pantalla Saldos

**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-16-mostrar-sumas-saldos-cuentas-contables.md (v1)
**Spec reference:** AC-08, UI-01 (filtros en la URL, selector de período), Test Specification (spec de la pantalla)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Ramas nuevas de `balances-page.component.ts` sin ninguna prueba: `onPeriod`, `matchingPeriod`, `apply` (escritura de filtros en la URL vía router), `clearFilters`, `classLabel` sin clasificación, `appliedFilters` para Desde/Hasta/Cuenta y `balanceFiltersToQuery` con `date_to`. El selector de período es una desviación declarada que sustituye a `period_id`, por lo que su comportamiento (rellenar Desde/Hasta y re-seleccionar el período coincidente) es la única vía de UI para AC-06.

## Expected behavior
Cada rama nueva con prueba; elegir un período rellena fechas y navega con query params; limpiar filtros restablece URL y selector.

## Actual behavior
Cobertura de `balances-page.component.ts`: 78,02 % sentencias (71/91) y 57,89 % ramas. Líneas sin cubrir: 37, 90-93, 100, 104, 135, 140-147, 155, 169, 173-179. (Total global del proyecto: 86,83 % sentencias / 78,21 % ramas.)

## Evidence
`npx ng test --watch=false --browsers=ChromeHeadless --code-coverage` → `TOTAL: 1546 SUCCESS`; informe `coverage/oreva/app/features/accounting/pages/balances/index.html`: 78.02% (71/91) statements, 57.89% branches; informe por línea marca `onPeriod`, `clearFilters`, `apply`, `matchingPeriod` como `cstat-no`.
