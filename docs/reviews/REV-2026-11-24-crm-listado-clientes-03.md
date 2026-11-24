# REV-2026-11-24-crm-listado-clientes-03: Filtro de sucursal acepta almacenes inactivos

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-24-crm-listado-clientes.md (v1)
**Spec reference:** AC-02 (lenguaje ubicuo: Sucursal = almacén activo)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`WarehouseDirectoryAdapter.exists` usa `inventory.services.get_warehouse_names`, que devuelve almacenes activos o no. El plan define Sucursal como almacén activo.

## Expected behavior
Un almacén inactivo de la empresa se rechaza con 400, o se documenta que se admite (el selector de la UI solo lista activos).

## Actual behavior
Un `warehouse_id` de un almacén inactivo propio devuelve 200 con sus clientes (sin prueba que lo fije).

## Evidence
backend/modules/inventory/services.py:177-181 docstring: 'Nombre de cada almacén indicado de la empresa, activo o no'. backend/modules/crm/infrastructure/adapters.py WarehouseDirectoryAdapter.exists.
