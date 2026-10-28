# REV-2026-10-28-registrar-existencias-iniciales-05: El resumen muestra la fecha como 2026-10-28 en vez de dd/MM/yyyy
**Status:** Resolved (corregido en delivery-build, pendiente de re-verificación del Quality Gate)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-27-registrar-existencias-iniciales.md (v1)
**Spec reference:** UI-03, design-system.md (fechas dd/MM/yyyy)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`stock-opening.component.html` imprime `form.controls.movementDate.value` (ISO) en el resumen.

## Expected behavior
Fecha con formato `dd/MM/yyyy`, como en el resto del producto (movimientos ya la muestra así).

## Actual behavior
El resumen dice «Fecha 2026-10-28».

## Evidence
Revisión visual, paso «Revisar apertura».
