# REV-2026-10-29-politica-stock-negativo-02: El 409 insufficient_stock (API-02) no es alcanzable por ningún endpoint ni está probado a nivel HTTP

**Status:** Open
**Severity:** Low
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-10-29-politica-stock-negativo.md (v1)
**Spec reference:** AC-02, API-02; Test Specification > Integration tests (casos con BD real: 409 por apertura/ajuste)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
El plan pide una integración 'salida insuficiente por apertura/ajuste devuelve 409 con el cuerpo de API-02'. Pero la apertura solo registra entradas y el ajuste nunca deja saldo negativo (el propio TASK lo documenta), de modo que ningún endpoint actual puede devolver `insufficient_stock`. Los `except InsufficientStock` añadidos en `adjustment_views.py` y `stock_views.py` quedan sin cobertura y el cuerpo solo se prueba instanciando `InsufficientStockConflict` (`InsufficientStockBodyTests`).

## Expected behavior
La especificación debería reflejar que el 409 solo se ejerce cuando existan los endpoints de reversión/entrega (PB-INV-008 y la historia de entrega) y el plan no debería exigir una integración inalcanzable; o bien el cableado se cubre con un test que fuerce la excepción en la vista.

## Actual behavior
Contrato API-02 verificado solo por unit sobre la clase de excepción (`status_code`, `code`, `product`, `warehouse`, `requested='5.000'`, `available='2.000'`); sin test de vista. Los handlers de las vistas son código muerto hasta la próxima historia. No bloquea.

## Evidence
`backend/modules/inventory/tests/test_negative_policy.py::InsufficientStockBodyTests` (únicos tests del cuerpo); `git diff` muestra los `except InsufficientStock` en `api/adjustment_views.py` y `api/stock_views.py` sin test que los alcance.

## Revisión (Quality Gate ciclo 2)
Sigue abierto: consecuencia aceptada del alcance (Ventas/reversión llegan después); Low, no bloquea.
