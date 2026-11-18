# Filtros de Saldos con apariencia degradada en ancho ~800 px (chevron solapado, botón fuera de la tarjeta)

**Status:** Resolved (53e31d6, verificado en la segunda pasada del Quality Gate)
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-16-mostrar-sumas-saldos-cuentas-contables.md (v1)
**Spec reference:** UI-01 / DDR (filtros en fila); design-system.md §8 (responsive, legibilidad)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
En la inspección con el panel de navegador a 800 px de ancho (breakpoint md, columnas `col-md-2`), el texto «Sin período» del selector de período se solapa con el chevron, las fechas se truncan («10/11/20…») y el botón «Limpiar filtros» queda pegado/desbordando el borde derecho de la tarjeta. A 390 px los filtros se apilan bien y la tabla hace scroll horizontal interno sin scroll de página (scrollWidth 390 = clientWidth 390; tabla 800 px en contenedor de 294 px).

## Expected behavior
Filtros legibles y contenidos en la tarjeta en anchos intermedios (p. ej. `col-lg-*` en lugar de `col-md-*` o `flex-wrap` con anchos mínimos).

## Actual behavior
Ver descripción (captura a 800x600 de `/pocketbiz/accounting/balances?date_from=2026-11-10&date_to=2026-12-31`).

## Evidence
Medición JS a 390 px: `{"cw":390,"sw":390,"tbl":800,"tblc":294}`; captura a 800x600: select «Sin perío⌄», fechas «10/11/20…», botón «Limpiar filtros» en el borde de la tarjeta. No se pudo verificar 1440 px ni el tema oscuro (ver informe).
