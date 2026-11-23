# REV-2026-11-23-pedido-pantalla-unica-creacion-10: Sin saldo visible en el detalle de consulta (preparación y listo)

**Status:** Open
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-23-pedido-pantalla-unica-creacion.md (v3)
**Spec reference:** AC-14, AC-11
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
En `IN_PREPARATION` y `READY` el detalle ya no tiene la tarjeta de Cobro: el listado de pagos solo muestra «Pagado» y el saldo pendiente solo se ve en el modal de pago y, en `DELIVERED`, en el aviso de saldo. Cumple la Specification (los importes son Subtotal, Descuento y Total), pero es una pérdida respecto de la pantalla anterior.

## Expected behavior
Poder ver el saldo pendiente sin abrir el modal.

## Actual behavior
Ver evidencia.

## Evidence
`order-detail.component.html`, bloque `compactLayout`. Decidir si se añaden «Pagado» y «Saldo» a los importes (cambio de Specification: requiere aprobación).
