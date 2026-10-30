# REV-2026-10-29-catalogo-usos-del-producto-01: La lista y el detalle muestran el precio de productos no vendibles

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-29-catalogo-usos-del-producto.md (v1)
**Spec reference:** UI-03 (lista: precio «—» si no vendible); INV-05 (el precio guardado se conserva al dejar de vender)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Por INV-05 un producto con `can_sell=false` conserva su `sale_price`. La columna Precio de la lista usa `row.salePrice ?? '—'`, de modo que solo muestra «—» cuando el precio es nulo, no cuando el producto no se vende.

## Expected behavior
UI-03 / DDR: la columna Precio muestra «—» si el producto no es vendible (`canSell=false`), tenga o no un precio conservado.

## Actual behavior
Un producto que se vendía y se apagó «Se puede vender» sigue mostrando su precio en la lista (y en el detalle, fila «Precio de venta»), contradiciendo la columna «Uso» (sin badge «Venta»).

## Evidence
- `frontend/panel_admin/src/app/features/products/pages/product-list/product-list.component.html`: `{{ row.salePrice ?? '—' }}`
- `frontend/panel_admin/src/app/features/products/pages/product-detail/product-detail.component.html`: `{{ p.salePrice ?? 'No se vende' }}`
- El formulario siempre reenvía el precio escrito aunque el campo esté oculto (product-form.component.ts, comentario «conserva el precio que ya tenía»).
- Revisión por código; no ejercido en navegador.
