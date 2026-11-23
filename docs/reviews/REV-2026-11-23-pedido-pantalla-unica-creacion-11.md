# REV-2026-11-23-pedido-pantalla-unica-creacion-11: Sin prueba de la recarga tras `stale` del modal de pago

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-23-pedido-pantalla-unica-creacion.md (v3)
**Spec reference:** AC-13
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
La rama `STALE_ORDER_FOR_PAYMENT` de `openPaymentDialog` (toast de error y `reload()`) no tiene prueba en `order-detail`; solo `payment-dialog.spec` prueba el `dismiss` con ese motivo. La rama equivalente de la entrega sí está probada.

## Expected behavior
Prueba que verifique el toast y la relectura del pedido.

## Actual behavior
Ver evidencia.

## Evidence
`order-detail.component.ts` (`openPaymentDialog`) y `order-detail.component.spec.ts`.
