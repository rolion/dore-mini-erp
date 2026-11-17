# REV-2026-11-17-contabilizar-ventas-cobros-sin-duplicar-15: Fixtures del panel aún modelan SALE_RECOGNITION como evento visible

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-17-contabilizar-ventas-cobros-sin-duplicar.md (v3)
**Spec reference:** Limpieza
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`posting-fixtures.ts` y specs del panel siguen con el evento antiguo.

## Expected behavior
Fixtures alineados con el catálogo vigente.

## Actual behavior
Sin efecto funcional: los datos vienen del servidor.

## Evidence
`frontend/panel_admin/src/app/features/accounting/testing/posting-fixtures.ts`. Hallado por el Quality Gate v3 (subagente aislado, 2026-11-17).
