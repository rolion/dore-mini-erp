# REV-2026-10-27-inventario-stock-almacenes-unidades-06: Aviso de unidad en uso con estilo distinto al del DDR

**Status:** Resolved
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-10-27-inventario-stock-almacenes-unidades.md (v1)
**Spec reference:** UI-04
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Aviso de unidad en uso con estilo distinto al del DDR.

## Expected behavior
`alert-warning` para bloqueos.

## Actual behavior
Usaba `alert-info`.

## Evidence
unit-dialog.component.html.

## Resolution
Cambiado a `alert-warning`.
