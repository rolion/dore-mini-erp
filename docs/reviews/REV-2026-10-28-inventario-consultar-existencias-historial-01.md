# REV-2026-10-28-inventario-consultar-existencias-historial-01: Sin prueba de 403 para el nuevo detalle GET /api/stock/<product_id>/<warehouse_id>/

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-28-inventario-consultar-existencias-historial.md (v1)
**Spec reference:** Test Specification > Integration tests ("403 sin módulo"); Authorization / permissions; API-02
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El plan exige verificar 403 sin módulo `inventory` y para no administradores. Los tests existentes (`test_stock.py:238` y `:266`) solo ejercitan `GET /api/stock/` (lista). El endpoint nuevo de detalle (`StockDetailView`) no tiene prueba de 403, ni figura en la matriz de `modularity/tests/test_enforcement.py`.

## Expected behavior
Una prueba que confirme 403 en el detalle con el módulo deshabilitado y con un usuario no administrador.

## Actual behavior
La protección existe en código (`required_modules = ('inventory',)` y permiso por defecto) pero no está cubierta por un test para el endpoint nuevo.

## Evidence
`grep "stock" backend/modules/modularity/tests/test_enforcement.py` sin resultados; `test_stock_query.py` no contiene casos 403. 796 tests pasan.
