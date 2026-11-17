# REV-2026-11-17-asientos-manuales-navegacion-contable-04: Texto secundario ilegible en tema oscuro

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-17-asientos-manuales-navegacion-contable.md (v1)
**Spec reference:** design-system §7/§8 (claro y oscuro)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build (frontend)

## Description
Las notas con `text-body-secondary` (p. ej. «Los asientos confirmados no se editan…» en el detalle, y la nota de «Otras configuraciones») no se leen en tema oscuro.

## Expected behavior
Texto con contraste AA sobre la tarjeta oscura.

## Actual behavior
El panel de la plantilla activa `body.dark` pero no `data-bs-theme`, de modo que `text-body-secondary` sigue siendo gris oscuro sobre tarjeta oscura. El mismo patrón existe en otras pantallas (Entradas, detalle de Entradas); las nuevas lo heredan.

## Evidence
Navegador integrado, 1440 px, `body.dark`: color computado `rgba(33, 37, 41, 0.75)` sobre fondo de tarjeta `rgb(22, 25, 42)` (~1,1:1). Además el `alert-success` (texto blanco sobre verde #54ca68) tiene contraste bajo, igual que en el resto de la plantilla.

## Resolución
Corregido (2026-11-17): `.dark .text-body-secondary` usa `$color-font` (#96a2b4 sobre #16192a, 6,7:1) en `assets/scss/skins/_dark.scss`, lo que también arregla las pantallas anteriores que usaban esa clase; los avisos de éxito del detalle pasan al estilo tenue (`bg-success-subtle text-success-emphasis`). Verificado en el navegador con `body.dark`.
