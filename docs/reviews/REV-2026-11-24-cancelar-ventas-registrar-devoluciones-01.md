# REV-2026-11-24-cancelar-ventas-registrar-devoluciones-01: El estado RETURNED sigue contando como compra y saldo en el perfil del cliente y en la lista de pedidos

**Status:** Resolved (corregido en delivery-build, 2026-11-24)
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-24-cancelar-ventas-registrar-devoluciones.md (v1)
**Spec reference:** INV-07, AC-10 (coherencia de pedido válido en todo el producto)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El backend excluye `RETURNED` de `read_queries.valid_orders`, pero el frontend calcula «pedido válido» por su cuenta comparando solo con `CANCELLED` en dos lugares que la tarea no tocó, por lo que un pedido devuelto sigue contándose.

## Expected behavior
INV-07: `RETURNED` y `CANCELLED` no son pedido válido. El perfil del cliente no debe contar un pedido devuelto como compra ni sumar su saldo (un pedido devuelto sin cobros no es deuda del cliente). La lista de pedidos no debe pintar en rojo el saldo de un pedido devuelto.

## Actual behavior
- `frontend/panel_admin/src/app/features/customers/models/customer-purchase-summary.ts:22`: `orders.filter((order) => order.status !== CANCELLED_STATUS)`; con un pedido `RETURNED` se suman `orderCount`, `totalPurchased`, `outstandingBalance` y `lastPurchaseDate` (un pedido devuelto sin cobros aparece como saldo por cobrar del cliente).
- `customers/components/customer-purchase-history/customer-purchase-history.component.ts:37`: `isCancelled` solo reconoce `CANCELLED`, así que el devuelto no se atenúa/etiqueta como anulado.
- `sales/pages/order-list/order-list.component.ts:289-291` (`owes`) y `:294` (`showsBalance`): solo consideran `CANCELLED`; un `RETURNED` con `balance != 0` se muestra como deuda en rojo.
La tarea no modificó estos archivos (ver `git diff --stat`), y ninguna prueba cubre `RETURNED` en ellos.

## Evidence
```
$ grep -rn "CANCELLED" frontend/panel_admin/src/app/features/customers --include=*.ts
customer-purchase-summary.ts:5:export const CANCELLED_STATUS = 'CANCELLED';
customer-purchase-summary.ts:22:  const valid = orders.filter((order) => order.status !== CANCELLED_STATUS);
customer-purchase-history.component.ts:37:    return order.status === CANCELLED_STATUS;
$ sed -n 289,291p order-list.component.ts
    return row.status !== 'CANCELLED' && row.balance !== ZERO_AMOUNT;
$ git diff --stat origin/main...HEAD -- frontend/panel_admin/src/app/features/customers   (sin salida: no tocado)
```
