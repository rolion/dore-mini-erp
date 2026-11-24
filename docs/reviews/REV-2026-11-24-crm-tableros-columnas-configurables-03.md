# REV-2026-11-24-crm-tableros-columnas-configurables-03: El botón «Nuevo tablero» de la cabecera mezcla texto con el botón circular

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-24-crm-tableros-columnas-configurables-v1 (docs/plans/PLAN-2026-11-24-crm-tableros-columnas-configurables.md)
**Spec reference:** UI-05; design-system.md §3 «Alta rápida en cabecera de lista» (`btn btn-icon icon-left btn-primary rounded-button` solo con icono `add`)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El patrón de alta rápida es un botón circular solo con icono, con `title` y `aria-label` (referencia `customer-list`).

## Expected behavior
`<button class="btn btn-icon icon-left btn-primary rounded-button" title=… aria-label=…><i class="material-icons">add</i></button>`.

## Actual behavior
`crm-board.component.html` añade el texto «Nuevo tablero» dentro del botón circular. En tema claro queda recortado (solo se ve «+»); en tema oscuro el texto se rompe en vertical («N u e v o …») junto al botón.

## Evidence
Captura en tema oscuro a 1440 px: letras apiladas verticalmente bajo el «+» de la cabecera de la tarjeta.
