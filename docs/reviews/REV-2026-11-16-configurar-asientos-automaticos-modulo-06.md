# REV-2026-11-16-configurar-asientos-automaticos-modulo-06: Las tablas de vista previa muestran una barra de desplazamiento vertical interna

**Status:** Resolved
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-16-configurar-asientos-automaticos-modulo.md (v1)
**Spec reference:** AC-14, UI-01, design-system.md §8
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Segunda pasada, navegador integrado, `/es/pocketbiz/sales/settings` (pestaña «Asientos automáticos») y `/es/pocketbiz/expenses/settings`, a 375x812 y a 1440x900, tema claro.

## Expected behavior
Las tablas de «Asientos previstos» se ven completas, sin barras de desplazamiento internas (ni horizontal ni vertical).

## Actual behavior
Cada `.table-responsive` de la vista previa tiene `overflow-y: auto` y su contenido excede en 1 px (p. ej. `scrollHeight` 128 vs `clientHeight` 127 en Ventas; 133 vs 132 en Gastos; 130 vs 129 en «Cobrar una venta» a 375 px). Resultado: aparece una barra vertical gris (con flechas en escritorio) dentro de cada tarjeta de evento. El recorte horizontal de REV-03 sí está resuelto (`scrollWidth` = `clientWidth` = 231 px a 375 px; el documento no desborda).

## Evidence
Medición por JS en la página y capturas a 375 px y 1440 px (barra vertical visible junto a la columna Cuenta). Suele corregirse con `overflow-y: hidden` en el contenedor de la vista previa o evitando el desbordamiento subpíxel de la tabla.

## Resolution
`.preview-scroll { overflow-y: hidden }` en las tablas de vista previa (sin barra vertical por desbordamiento de 1 px).
