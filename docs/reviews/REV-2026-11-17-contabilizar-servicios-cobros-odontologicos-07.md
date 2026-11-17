# REV-2026-11-17-contabilizar-servicios-cobros-odontologicos-07: Alerta compartida: margen y estilo distintos a los de Ventas

**Status:** Resolved (parcial)
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-17-contabilizar-servicios-cobros-odontologicos.md (v1)
**Spec reference:** UI-03
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
La alerta compartida usa `bg-warning-subtle` y un `mt-2` interno; Ventas usaba `alert-warning`/`alert-link`. `titleKey`/`linkKey` no estaban documentados.

## Expected behavior
Cobertura de pruebas y documentación coherentes con la Specification y el sistema de diseño.

## Actual behavior
Ver descripción.

## Evidence
Quality Gate, 2.ª pasada (subagente aislado, HEAD b778d3d). `design-system.md` §3 documenta ahora `titleKey`/`linkKey`. El aspecto en Ventas (claro/oscuro) no se ha visto en navegador: pendiente de revisión visual.
