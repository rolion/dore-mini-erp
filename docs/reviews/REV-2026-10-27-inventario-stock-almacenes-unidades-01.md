# REV-2026-10-27-inventario-stock-almacenes-unidades-01: Specs del sidebar rotos por el submenú nuevo

**Status:** Resolved
**Severity:** High
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-27-inventario-stock-almacenes-unidades.md (v1)
**Spec reference:** UI-05; regresión AC-09/AC-20/AC-22/UI-01 de PB-CFG-001
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Specs del sidebar rotos por el submenú nuevo.

## Expected behavior
La suite existente sigue verde.

## Actual behavior
2 specs de `sidebar-menu.spec.ts` fallaban (`Expected 20 to be 19`, submenú de Inventario con 3 ítems).

## Evidence
Karma completo: TOTAL 73 FAILED vs línea base 71.

## Resolution
Spec actualizado (20 títulos; submenú Inicio, Almacenes y unidades, Ajustes). Karma completo tras el arreglo: 71 FAILED (línea base), 567 SUCCESS.
