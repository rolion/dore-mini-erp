# REV-2026-10-28-registrar-existencias-iniciales-04: El desplegable de productos queda recortado dentro de la tabla de líneas
**Status:** Resolved (corregido en delivery-build, pendiente de re-verificación del Quality Gate)
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-27-registrar-existencias-iniciales.md (v1)
**Spec reference:** UI-02, DDR (selector con búsqueda)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El `ng-select` de cada línea está dentro de `.table-responsive` (overflow), que recorta el panel de opciones.

## Expected behavior
El panel de opciones se ve completo sobre la tabla (p. ej. `appendTo="body"`), con varias opciones visibles.

## Actual behavior
Al abrir el selector de la línea 1 solo se ve una opción y aparece una barra de desplazamiento dentro de la tabla; en la línea 2 se ve media opción (la de «Aceite» deshabilitada). Hay que escribir para encontrar el producto.

## Evidence
Revisión visual en el navegador integrado (escritorio 1440 px, claro): al abrir «Buscar producto» el panel queda cortado en el borde inferior de la tabla.
