# REV-2026-10-29-ventas-inventario-salida-al-entregar-01: La vista previa (GET) puede escribir al sembrar el almacén predeterminado

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-29-ventas-inventario-salida-al-entregar.md (v1)
**Spec reference:** AC-11 ("no escribe nada"), API-01
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`GET /api/orders/<id>/delivery-preview/` llama a `StockOutputAdapter.active_warehouses()` -> `inventory.services.list_active_warehouses`, que ejecuta `repository.ensure_default()` (INSERT del almacén "Principal" si la empresa no tiene ninguno).

## Expected behavior
La vista previa es de solo lectura (AC-11); no crea filas.

## Actual behavior
En una empresa sin almacenes, un GET de preview crea el almacén predeterminado. El test `test_preview_lists_lines_balances_and_policy_without_writing` solo compara `StockMovementModel.objects.count()`, no almacenes, y siembra antes el almacén, por lo que no detecta el caso. Efecto acotado (mismo sembrado que hace Inventario al listar almacenes), pero contradice la letra de AC-11 y un GET no debería mutar.

## Evidence
`backend/modules/inventory/services.py:150-154`:
```
def list_active_warehouses(company_id):
    repository = DjangoWarehouseRepository(company_id)
    repository.ensure_default()
    return [... repository.list(active=True)]
```
Invocado desde `PreviewOrderDelivery.execute` (`sales/application/delivery.py`) vía `self.stock.active_warehouses()`. Verificado por lectura de código; no se ejecutó un caso dedicado.

## Resolution
`inventory.services.list_active_warehouses` ya no llama a `ensure_default()`: el preview (y la entrega) solo leen. Una empresa sin almacenes ve «No hay un almacén activo…» y el almacén predeterminado se siembra al abrir Inventario → Almacenes, como siempre. Prueba nueva: `DeliveryPreviewTests.test_preview_writes_nothing_even_without_warehouses`.
