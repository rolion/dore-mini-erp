# REV-2026-11-20-reporte-ingresos-egresos-contabilidad-05: El ratón no funciona en el selector de meses

**Status:** Fixed
**Severity:** High
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-20-reporte-ingresos-egresos-contabilidad.md (v1)
**Spec reference:** AC-05, UI-01
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Reportado por el usuario: en el filtro Mes la lista se abría y se podía desplazar, pero un clic en una opción no la seleccionaba y el × de cada mes elegido no lo quitaba; solo funcionaba con teclado (escribir + Enter, Retroceso).
## Expected behavior
Elegir y quitar meses con el ratón.
## Actual behavior
`monthOptions` era un getter que devolvía un arreglo nuevo con objetos nuevos en cada ciclo de detección de cambios; `ng-select` reconstruía las opciones entre el *mousedown* y el *click* y el clic se perdía.
## Evidence
Corregido: `monthOptions` es ahora un campo que se recalcula solo cuando cambian el reporte o los períodos, y conserva la misma referencia si las opciones no cambian. Prueba de regresión añadida. Verificado en el navegador con clics reales: elegir Febrero y Marzo con el ratón (totales 23000.00 / 11500.00 / 11500.00), quitar Febrero con su ×, y limpiar todo con el × general (vuelven los 12 meses). La lista además queda abierta tras elegir, lo que resuelve REV-04. Suite del frontend: 1761 pruebas OK; `ng lint` OK. Esta falla no la detectaron mis pruebas de componente ni el Quality Gate porque no simulaban un clic real sobre `ng-select`; mi revisión visual anterior solo usó teclado.
