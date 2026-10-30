# REV-2026-10-29-ventas-inventario-salida-al-entregar-02: Falta prueba de aislamiento entre empresas con mismos nombres (AC-15)

**Status:** Resolved
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-29-ventas-inventario-salida-al-entregar.md (v1)
**Spec reference:** AC-15, Test Specification (tabla AC->verificacion: "Integracion con dos empresas")
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El plan exige una integracion con dos empresas que tengan los mismos nombres de producto/almacen y verifique que no se afectan (saldos y movimientos independientes).

## Expected behavior
Una prueba que entregue pedidos en dos empresas con productos y almacenes homonimos y compruebe que saldos, movimientos y `stock_output` de cada una no se mezclan.

## Actual behavior
`test_delivery_inventory.py` cubre solo: almacen ajeno rechazado (400) y pedido de otra empresa 404 (preview/deliver) en `WarehouseRulesTests.test_foreign_or_unknown_warehouse_is_rejected` y `DeliveryPreviewTests.test_preview_requires_a_ready_order_of_the_company`. No hay prueba con datos homonimos ni de saldos aislados tras una entrega. El codigo filtra por `company_id` en los repositorios (revision manual sin hallazgos), por lo que el riesgo es de cobertura, no un defecto observado.

## Evidence
`grep -n "make_company\|Empresa" backend/modules/sales/tests/test_delivery_inventory.py` -> solo `Empresa A` (base), `Empresa B` (almacen ajeno x2), `Empresa C` (otro usuario / concurrencia); ningun test crea productos o almacenes con el mismo nombre en dos empresas ni compara saldos entre ellas.

## Resolution
Prueba nueva `TwoCompaniesTests.test_same_names_in_two_companies_never_mix_stock_or_movements`: dos empresas con producto y almacén homónimos; la entrega de A no toca el saldo ni los movimientos de B, B entrega la suya con su almacén, cada una ve solo sus movimientos y el almacén homónimo de la otra se rechaza (400).
