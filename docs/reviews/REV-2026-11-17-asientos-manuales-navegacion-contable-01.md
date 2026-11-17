# REV-2026-11-17-asientos-manuales-navegacion-contable-01: Regularizar pagos históricos queda sin ningún enlace visible

**Status:** Resolved
**Severity:** Medium
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-11-17-asientos-manuales-navegacion-contable.md (v1)
**Spec reference:** AC-09 («Entradas y Regularizar siguen operativos por URL con enlaces visibles»)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build (frontend)

## Description
Al quitar el ítem del menú, la pantalla /pocketbiz/accounting/regularization dejó de ser alcanzable desde la UI.

## Expected behavior
Cada pantalla conservada (Entradas y Regularizar) tiene al menos un enlace visible (p. ej. en Movimientos junto a «Ver entradas anteriores» o en Otras configuraciones).

## Actual behavior
La ruta existe en app.routes.ts, pero no hay ningún routerLink a ella. Solo Entradas tiene enlace (journal-list.component.html:69). El design-system §6 documenta «siguen por URL», lo que contradice la letra de AC-09.

## Evidence
grep de 'accounting/regularization' en src/app (html/ts, sin specs): solo aparece la definición de ruta en app.routes.ts:150 y routes.json ya no contiene REGULARIZATION.

## Resolución
Corregido en delivery-build (2026-11-17): enlace a Regularizar en Configuración y redirección de marcadores `?tab=` antiguos, con pruebas.
