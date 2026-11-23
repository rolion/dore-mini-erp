# REV-2026-11-23-pedido-pantalla-unica-creacion-09: Marca de fila con faltante por nombre y `toFieldErrors` frágil con `null`

**Status:** Fixed (pendiente de re-revisión)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-23-pedido-pantalla-unica-creacion.md (v1)
**Spec reference:** AC-06
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`isShort` compara por `productName` (dos productos con el mismo nombre se marcarían a la vez). `toFieldErrors` lanzaría `TypeError` ante un `null` dentro de la lista de errores (no ocurre con el contrato actual).

## Expected behavior
Identificar por id; tolerar entradas no objeto.

## Actual behavior
Ver evidencia.

## Evidence
`order-create.component.ts` (`isShort`), `orders-api.service.ts` (`toFieldErrors`).

## Resolución
`isShort` y el `track` comparan por `productId` (`StockShortage.productId`); `toFieldErrors` tolera `null`. Pruebas añadidas.
