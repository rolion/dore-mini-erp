# REV-2026-10-28-registrar-existencias-iniciales-07: Conflicto con el PR #21 (PB-INV-004): mismo modelo `StockMovementModel` y misma migración `inventory/0002`
**Status:** Open
**Severity:** High
**Category:** ARCHITECTURE
**Related plan:** docs/plans/PLAN-2026-10-27-registrar-existencias-iniciales.md (v1)
**Spec reference:** AC-02, AC-03 (movimiento de apertura y saldo); ADR de este task
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
El [PR #21](https://github.com/rolion/dore-mini-erp/pull/21) (`task/TASK-inventario-movimientos-trazables`, PB-INV-004, en PUBLISH) también crea `StockMovementModel` (tabla `inventory_stock_movement`, con `kind`, `occurred_at`, `source_type/id/line`, `status`, `reverses_id`, usuario) y `inventory/migrations/0002_stock_movements.py`. Este task crea otro `StockMovementModel` (tipo `opening`, `opening_id`, `movement_date`) y `0002_stock_movements_balances.py`. Los dos parten de `main` tras el PR #20.

## Expected behavior
Un único modelo de movimientos y una cadena de migraciones lineal: la apertura debería crear sus movimientos con el modelo de PB-INV-004 (o viceversa) y añadir solo lo propio (saldos, restricción de una apertura por producto+almacén).

## Actual behavior
Al fusionar ambos hay dos migraciones `0002` en `inventory` y dos clases con el mismo nombre y tabla. La base de desarrollo local ya tiene aplicada la `0002_stock_movements` del PR #21: `migrate` con este branch falla con `relation "inventory_stock_movement" already exists` (se comprobó; no se modificó nada).

## Evidence
```
django.db.utils.ProgrammingError: relation "inventory_stock_movement" already exists
django_migrations: ('inventory', '0001_stock_units_warehouses'), ('inventory', '0002_stock_movements')
columnas de la tabla existente: id, company_id, product_id, kind, quantity, occurred_at, user_id, user_name, reference, reason, source_type, source_id, source_line, status, reverses_id, created_at, warehouse_id
```
Decisión pendiente del usuario: orden de integración (PB-INV-004 primero y rebase de PB-INV-003 sobre su modelo, o el contrario). Cambia el ADR y el plan de este task (Specification sin cambios).
