# REV-2026-11-17-contabilizar-ventas-cobros-sin-duplicar-12: Pruebas de integración faltantes: edición libre sin cobertura y asientos históricos intactos

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-17-contabilizar-ventas-cobros-sin-duplicar.md (v3)
**Spec reference:** AC-12 / AC-13
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Sin prueba de integración de «sin cobertura, edición libre», de la rama `AT_CONFIRM` de `locks_total`, ni aserción de que no se modifica ningún asiento histórico.

## Expected behavior
Pruebas que comparen asientos antes y después y cubran esas ramas.

## Actual behavior
Solo cubiertas con puerto falso o por inspección.

## Evidence
`SalesPostingAdapter.locks_total`; `TransitionTests`. Hallado por el Quality Gate v3 (subagente aislado, 2026-11-17).
