# REV-2026-11-16-periodos-fiscales-por-empresa-06: Estado vacío sin botón «Crear período»

**Status:** Resolved
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-16-periodos-fiscales-por-empresa.md (v1)
**Spec reference:** UI-01
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El DDR pide botón «Crear período» en el vacío; solo hay texto que remite al «+» del encabezado.

## Expected behavior
Añadir el botón o ajustar el DDR.

## Actual behavior
Ver descripción.

## Evidence
Quality Gate (subagente aislado), periods-tab.component.html (estado vacío). Backend 1678 OK; frontend 1430 OK (2 de 3 corridas, ver nota del flake preexistente `screens-i18n.spec.ts:58-65`, ajeno al diff).
