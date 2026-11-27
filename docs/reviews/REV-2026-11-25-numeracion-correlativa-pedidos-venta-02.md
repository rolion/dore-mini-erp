# REV-2026-11-25-numeracion-correlativa-pedidos-venta-02: Falta la prueba de importación de ventas con fecha sin período o período cerrado (AC-10)

**Status:** Resolved
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-25-numeracion-correlativa-pedidos-venta.md (v1)
**Spec reference:** AC-10; Test Specification > Integration tests («Importación de ventas: fila rechazada con el código del período»); Acceptance criteria mapping (AC-10)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
AC-10 exige que en la importación de ventas una fecha sin período o con período cerrado rechace solo esa fila con el mismo código (`fiscal_period_missing` / `fiscal_period_closed`). El código lo soporta (`sales/services.py:import_delivered_sale` captura `OrderRuleViolation` y lanza `ImportRejected(exc.code, ...)`), pero no hay ninguna prueba que lo ejercite.

## Expected behavior
Una prueba de importación (servicio `import_delivered_sale` o API de `data_import`) con una fila cuya fecha no cae en ningún período y otra en período cerrado: esas filas quedan rechazadas con el código correspondiente, la fila con período válido se importa y recibe `NV-`, y no quedan pedidos NEW huérfanos de la fila rechazada.

## Actual behavior
Los cambios en `data_import/tests/test_api_integration.py` solo añaden `open_test_period(...)` a los `setUp` para que las pruebas heredadas sigan pasando. `grep -rln "fiscal_period_missing\|fiscal_period_closed\|import_delivered_sale" backend/modules --include=*.py` solo encuentra: `data_import/infrastructure/adapters.py`, `expenses/...`, `sales/application/ports.py`, `sales/infrastructure/adapters.py`, `sales/services.py` y las tres suites `test_order_numbering*.py`/`test_order_number_domain.py` (ninguna de importación). Rama nueva (captura `OrderRuleViolation` por falta/cierre de período en la importación) sin prueba. Tampoco se verifica que la fila rechazada revierta el pedido NEW creado antes por `CreateOrder` (depende de que `gateway.atomic()` envuelva cada fila).

## Evidence
- Búsqueda anterior (salida literal de archivos listados).
- `git diff origin/main...HEAD -- backend/modules/data_import` solo contiene 6 líneas añadidas de `open_test_period`.

## Resolución
Resuelto: `SalesImportFiscalPeriodTests` en `data_import/tests/test_api_integration.py` (filas sin período → `fiscal_period_missing` y ningún pedido; fila en período cerrado → `fiscal_period_closed`, la otra se importa con número 1 y no quedan pedidos NEW huérfanos).
