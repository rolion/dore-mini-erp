# REV-2026-11-27-consultar-ordenes-seguimiento-estado-04: Celdas de la tabla de ingredientes y aria-valuetext de la barra de progreso

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-27-consultar-ordenes-seguimiento-estado.md (v2)
**Spec reference:** AC-06 / UI-04
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Los `<th>` de Consumo real y Diferencia dependen de `order.lot`, pero las `<td>` de `line.actualQuantity !== null`; la barra de progreso tiene `aria-valuenow` sin `aria-valuetext`.

## Expected behavior
Celdas condicionadas a `order.lot` como los encabezados; `aria-valuetext` legible (p. ej. «0 h 4 min de 1 h»).

## Actual behavior
Con lote y una línea sin consumo real la fila tendría menos celdas que el encabezado (hoy el backend lo registra al crear el lote, no ocurre); el lector de pantalla solo anuncia un porcentaje.

## Evidence
`order-detail.component.html` (Quality Gate aislado, 2026-11-27).
