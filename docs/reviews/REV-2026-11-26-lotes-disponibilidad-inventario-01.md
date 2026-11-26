# REV-2026-11-26-lotes-disponibilidad-inventario-01: Control previo de Ventas cuenta stock en refrigeración

**Status:** Resolved
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

## Resolution
Corregido con aprobación del usuario: `inventory.services.get_balances(..., unlotted=True)` y los adaptadores de Ventas (`sales/infrastructure/adapters.py`) e importación (`data_import/infrastructure/adapters.py`) lo usan, así el control previo ve solo el stock sin lote. Pruebas: `sales/tests/test_place_order.py::test_stock_in_a_refrigerating_lot_does_not_count_for_a_sale` (falla sin la corrección, comprobado por mutación) y `inventory/tests/test_lots.py::test_get_balances_can_exclude_lot_stock`. `costing` sigue usando el físico (valoración).
