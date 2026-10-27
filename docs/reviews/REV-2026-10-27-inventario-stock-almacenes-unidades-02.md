# REV-2026-10-27-inventario-stock-almacenes-unidades-02: Verificación propia acotada dejó pasar la regresión

**Status:** Resolved
**Severity:** Low
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-10-27-inventario-stock-almacenes-unidades.md (v1)
**Spec reference:** Test Specification (Regression)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Verificación propia acotada dejó pasar la regresión.

## Expected behavior
Correr la suite completa de frontend contra la línea base.

## Actual behavior
La verificación del TASK se acotó a products e inventory.

## Evidence
Ver REV-01.

## Resolution
Se corrió Karma completo y se compara con 71 fallos de línea base.
