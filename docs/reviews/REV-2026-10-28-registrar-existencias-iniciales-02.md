# REV-2026-10-28-registrar-existencias-iniciales-02: el backend acepta notación exponencial en la cantidad
**Status:** Resolved (verificado por el Quality Gate, ciclo 3, 2026-10-28)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-27-registrar-existencias-iniciales.md (v1)
**Spec reference:** INV-02, EDGE-02 («no numérica -> 400»)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`validate_quantity` (backend/modules/inventory/domain/stock.py) usa `Decimal(str)`, que acepta `1e3`, `+5`, dígitos Unicode, etc.

## Expected behavior
Solo texto decimal simple (`^\d+(\.\d+)?$`), igual que `quantityError` del frontend.

## Actual behavior
`quantity: "1e3"` -> 201 con cantidad `1000.000`. No hay riesgo de corrupción (el límite de magnitud y decimales sí se aplica; `1e20` y `1e-30` se rechazan), pero un cliente que no sea la UI puede registrar 1000 escribiendo «1e3».

## Evidence
```
PROBE {'lines': [{'product_id': '...', 'quantity': '1e3'}]} 201 ... "quantity":"1000.000"
PROBE ... 'quantity': 'Infinity' -> 400 ; '1e-30' -> 400 (3 decimales) ; 1e+20 -> 400 (supera máximo)
```
