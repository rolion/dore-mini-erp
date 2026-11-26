# REV-2026-11-25-numeracion-correlativa-pedidos-venta-03: La vista previa de devolución (`order_code`, API-03) no tiene prueba con el nuevo código

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-25-numeracion-correlativa-pedidos-venta.md (v1)
**Spec reference:** API-03; AC-11; Test Specification > Integration tests («API: ... vista previa de devolución»)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`sales/api/serializers.py:213` devuelve `'order_code': order.code` en la vista previa de devolución, que ahora es `NV-000001` para un pedido numerado. El plan pide una prueba de API para ese campo (API-03).

## Expected behavior
Una prueba de API que confirme un pedido, lo entregue y pida la vista previa de devolución, y compruebe `order_code == 'NV-000001'`.

## Actual behavior
`grep -rn "order_code\|'NV-" backend/modules --include=*.py | grep /tests/` (excluyendo `test_order_number*`) no devuelve ninguna aserción sobre `order_code`. La vista previa solo hereda cobertura indirecta por `test_api.py`. Riesgo bajo (el valor sale de la propiedad ya probada `Order.code`).

## Evidence
- Salida vacía del grep indicado.

## Resolución
Resuelto: `test_the_return_preview_uses_the_numbered_code` en `test_order_numbering.py` (`order_code == 'NV-000001'`).
