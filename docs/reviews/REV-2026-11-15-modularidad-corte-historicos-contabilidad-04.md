# REV-2026-11-15-modularidad-corte-historicos-contabilidad-04: Encabezado «Periodos sin cobertura» desproporcionado en «Corte y cobertura»

**Status:** Open
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-15-modularidad-corte-historicos-contabilidad.md (v1)
**Spec reference:** UI-01
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
En la pestaña «Corte y cobertura» el encabezado «Periodos sin cobertura» usa un `h3` con el tamaño por defecto de la plantilla (mucho mayor que el título de la sección, `h2` del `ngxTableHeader`), lo que rompe la jerarquía visual.

## Expected behavior
Subtítulo de tamaño coherente con el título de la pestaña (p. ej. clase de texto pequeña/negrita del sistema de diseño).

## Actual behavior
Encabezado grande, visible en escritorio y móvil.

## Evidence
Prueba visual en el navegador integrado (2026-11-15): captura de «Corte y cobertura» en escritorio y a 390 px muestra «Periodos sin cobertura» claramente más grande que «Corte y cobertura».
