# REV-2026-11-26-gestionar-recetas-produccion-03: Aviso de producto inactivo ausente en el formulario

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-26-gestionar-recetas-produccion.md (v1)
**Spec reference:** EDGE-05 / DDR
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El DDR pide `alert-warning` en el detalle y en el formulario; solo está en el detalle.

## Expected behavior
Aviso también al editar.

## Actual behavior
El error aparece solo al guardar (backend).

## Evidence
`recipe-form.component.html` sin aviso.
