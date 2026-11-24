# REV-2026-11-23-pedido-pantalla-unica-creacion-08: Anchos fijos `style="width: …"` inline en la tabla

**Status:** Accepted (deuda técnica)
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-23-pedido-pantalla-unica-creacion.md (v1)
**Spec reference:** UI-01
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`style="width: 140px"` y `style="width: 60px"` en las cabeceras; no son HEX ni fuentes, pero conviene una clase. Revisión visual (móvil, escritorio, claro/oscuro) no verificada.

## Expected behavior
Sin estilos en línea o clase de la plantilla.

## Actual behavior
Ver evidencia.

## Evidence
`order-create.component.html:154,156` (mismo patrón que `order-items`).

## Resolución
Aceptado como deuda técnica por el usuario (2026-11-23); sin cambio de código en esta tarea.
