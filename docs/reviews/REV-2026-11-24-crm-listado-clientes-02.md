# REV-2026-11-24-crm-listado-clientes-02: Faltan pruebas de fachadas y de exclusión de pedidos inválidos

**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-24-crm-listado-clientes.md (v1)
**Spec reference:** AC-05, INV-02, NFR sin N+1
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El plan (Test Specification y paso 1) pide pruebas de las fachadas `sales`/`customers`: pedidos cancelados y sin ítems excluidos, saldo con saldo>0, y consulta de agregados única por página. Solo existe `crm/tests/test_api.py` y el cambio en test_boundaries.

## Expected behavior
Pruebas que fallen si un pedido CANCELADO o sin ítems cuenta en `order_count`/saldo, si un pedido sobrepagado resta del saldo, y `assertNumQueries` constante con N clientes por página.

## Actual behavior
Ninguna prueba cubre esos casos; la regla depende de `valid_orders` solo indirectamente.

## Evidence
git diff origin/crm...HEAD --stat -- backend | grep tests -> solo crm/tests/__init__.py, crm/tests/test_api.py (168 líneas), sales/tests/test_boundaries.py. grep de 'cancel' / 'get_customer_commercial_summaries' / 'search_customers_for_crm' en crm/tests, sales/tests y customers/tests: sin coincidencias de pruebas nuevas.
