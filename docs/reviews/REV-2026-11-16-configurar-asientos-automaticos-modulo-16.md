# REV-2026-11-16-configurar-asientos-automaticos-modulo-16: El aviso global de categorías no nombra la categoría con cuenta inválida y las funde si comparten cuenta

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-16-configurar-asientos-automaticos-modulo.md (v4)
**Spec reference:** AC-03, AC-07, EDGE-03, AC-14
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`categoryIssues` construye, para una categoría activa con cuenta guardada inválida, `message = rowIssue(row)`, que es el texto del problema de la cuenta sin el nombre de la categoría; `issues` deduplica por `message`.

## Expected behavior
Cada línea del recuadro «Falta configurar N cuenta(s)» identifica la categoría afectada (como hace la línea «Falta la cuenta de gasto de la categoría «Categoria 002»»), y N cuenta una línea por categoría.

## Actual behavior
Con la categoría «Categoria 001» asignada a «Gasto viejo» (deshabilitada) la línea es «La cuenta «Gasto viejo» está deshabilitada; elija otra o actívela en Cuentas.» sin decir qué categoría. Si dos categorías usaran la misma cuenta deshabilitada, el texto es idéntico y `issues` las funde en una sola línea (N subcontado). Con 105 categorías sin configurar el recuadro es una lista de ~107 líneas (≈2000 px) sin resumen ni plegado; es legible pero empuja la configuración real fuera de la vista.

## Evidence
Navegador, /es/pocketbiz/expenses/settings (105 categorías): «Falta configurar 107 cuenta(s)» con 3 líneas de método + 1 línea de «Gasto viejo» sin categoría + 103 de «Falta la cuenta de gasto de la categoría «Categoria NNN»». Código: `posting-config-panel.component.ts` `categoryIssues` / `issues`. La spec REV-13 solo comprueba `toContain('«Gasto luz» está deshabilitada')`.

## Resolution
Las categorías con cuenta que ya no sirve aparecen por su nombre en el aviso global (un renglón por categoría) y la lista pasa a mostrar los 10 primeros faltantes con el resto plegado en «Ver N más». Pruebas añadidas.
