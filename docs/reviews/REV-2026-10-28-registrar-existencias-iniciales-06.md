# REV-2026-10-28-registrar-existencias-iniciales-06: Las columnas de la tabla de líneas cambian de ancho al elegir producto
**Status:** Resolved (verificado por el Quality Gate, ciclo 3, 2026-10-28)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-27-registrar-existencias-iniciales.md (v1)
**Spec reference:** UI-02
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
La tabla usa ancho automático: la columna Producto es angosta y se mueve al elegir un producto o mostrar un error.

## Expected behavior
Anchos estables (Producto ancho, Unidad base y Cantidad fijos).

## Actual behavior
El selector es estrecho (≈150 px en 1440 px) y las columnas se desplazan al cambiar el contenido; el aviso de historial también empuja el formulario hacia abajo.

## Evidence
Revisión visual en escritorio, capturas antes/después de elegir «Aceite».

## Verificación
Re-verificado en el navegador integrado tras el rebase (escritorio 1440 px): selector con las 5 opciones visibles sobre la tabla, fecha del resumen `28/10/2026` y columnas de ancho estable.
