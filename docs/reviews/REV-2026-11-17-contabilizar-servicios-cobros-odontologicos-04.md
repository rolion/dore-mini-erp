# REV-2026-11-17-contabilizar-servicios-cobros-odontologicos-04: HEX repetidos en el scss del diálogo de prestación

**Status:** Resolved
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-17-contabilizar-servicios-cobros-odontologicos.md (v1)
**Spec reference:** design-system §3
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`service-dialog.component.scss` repite `#16192a` y `#96a2b4` en el tema oscuro, con comentario de origen, igual que `payment-dialog`.

## Expected behavior
Cada rama contable y mensaje relevante cubierto y veraz; componentes y estilos coherentes con el sistema de diseño.

## Actual behavior
Ver descripción.

## Evidence
Quality Gate (subagente aislado, 2026-11-17). Con precedente; unificar cuando se normalicen los diálogos.

Resuelto: nuevo parcial `assets/scss/_dark-tokens.scss` (fuente única de `$color-dark-primary` y `$color-font`) usado por `skins/_dark.scss`, `payment-dialog` y `service-dialog`. Otros componentes (agenda, proformas, `proforma-decisions`) siguen repitiendo los HEX: deuda preexistente fuera de alcance.
