# REV-2026-11-27-consultar-ordenes-seguimiento-estado-03: Contraste de las etapas pendientes del stepper

**Status:** Open
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-27-consultar-ordenes-seguimiento-estado.md (v2)
**Spec reference:** UI-04 / design-system sección 8 (accesibilidad)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Las etapas pendientes se atenúan con `opacity: 0.75` sobre texto y marcador, y la fecha usa `text-muted`.

## Expected behavior
Atenuar con color de texto (`--bs-secondary-color`) y contraste mínimo 4.5:1 en tema claro y oscuro.

## Actual behavior
La opacidad reduce el contraste efectivo; el tema oscuro no se verificó.

## Evidence
`order-detail.component.scss`: `.order-step { opacity: 0.75; }` (Quality Gate aislado, 2026-11-27).
