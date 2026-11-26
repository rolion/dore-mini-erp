# REV-2026-11-26-lotes-disponibilidad-inventario-01: Control previo de Ventas cuenta stock en refrigeración

**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-26-lotes-disponibilidad-inventario.md (v1)
**Spec reference:** AC-09 / granel en refrigeración bloqueado para venta
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El control previo de stock al crear/confirmar un pedido usa el saldo físico total, que incluye lotes en refrigeración.

## Expected behavior
El control previo ve solo el stock sin lote (igual que la entrega) y rechaza si solo hay stock refrigerando.

## Actual behavior
Un pedido de un producto con 118 en un lote refrigerando y 0 sin lote pasa el control previo, consume su número fiscal y falla después en la entrega con 409 insufficient_stock. El stock no se corrompe: la regla de Inventario sí se impone.

## Evidence
Por lectura (no reproducido ejecutando, sin prueba que lo cubra): sales/application/placement.py:151-153 (_ensure_stock) → sales/infrastructure/adapters.py:143 → inventory/services.py get_balances (sin unlotted). El mismo get_balances lo usa data_import/infrastructure/adapters.py:101.
