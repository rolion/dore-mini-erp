# REV-2026-10-29-politica-stock-negativo-03: UI-01: el valor predeterminado se muestra «Desactivado» en lugar de «Bloqueado»

**Status:** Open
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-10-29-politica-stock-negativo.md (v1)
**Spec reference:** UI-01; DDR (Componentes/patrones elegidos)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
UI-01 y el DDR definen el texto 'Valor predeterminado: Bloqueado' junto al interruptor. La implementación usa un texto genérico por tipo booleano (`defaultLabel`: Activado/Desactivado). Está documentado como desviación 1 del TASK, pero no se actualizó el DDR ni el plan.

## Expected behavior
'Valor predeterminado: Bloqueado' (o DDR/plan actualizados a la decisión de un texto genérico).

## Actual behavior
Se muestra 'Valor predeterminado: Desactivado'; el historial sí usa Bloqueado/Permitido, con lo que la pantalla de configuración y el historial emplean vocabularios distintos.

## Evidence
`module-settings.component.ts` (`defaultLabel`, rama boolean) y TASK > Desviaciones #1.
