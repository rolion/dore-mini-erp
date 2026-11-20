# REV-2026-11-20-reporte-ingresos-egresos-contabilidad-04: El selector de meses pierde el foco tras cada elección

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-20-reporte-ingresos-egresos-contabilidad.md (v1)
**Spec reference:** AC-05
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Al elegir un mes, la navegación recarga el reporte y el `ng-select` múltiple se cierra y pierde el foco; para añadir un segundo mes hay que volver a abrirlo.
## Expected behavior
Poder elegir varios meses seguidos sin reabrir el selector.
## Actual behavior
Una elección por apertura. El filtro funciona: Enero y Marzo dieron totales 27500.50 / 9200.25 / 18300.25, correctos.
## Evidence
Prueba manual en el navegador integrado (escritorio). No bloqueante.
