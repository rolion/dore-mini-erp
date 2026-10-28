# REV-2026-10-28-registrar-existencias-iniciales-01: `lines` mal formado produce 500 o un 400 sin mensaje
**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-27-registrar-existencias-iniciales.md (v1)
**Spec reference:** API-01 (errores 400 por `lines[i].campo`), EDGE-05
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`_by_position` (backend/modules/inventory/api/stock_views.py) asume que `request.data['lines']` es una lista cuando el error de `lines` es un dict.

## Expected behavior
Un cuerpo con `lines` que no es una lista responde 400 con un mensaje legible (p. ej. «Se esperaba una lista de elementos»), nunca 500.

## Actual behavior
- `lines: 5` -> `TypeError: object of type 'int' has no len()` (500).
- `lines: "abc"` -> 400 `{"lines":[{},{},{}]}` (un dict vacío por carácter; el mensaje se pierde).
- `lines: {"a":1}` -> 400 `{"lines":[{}]}` (mensaje perdido).

## Evidence
Sonda temporal (ya eliminada) con APIClient, `config.settings.test`:
```
PROBE {'lines': 5} EXC TypeError object of type 'int' has no len()
PROBE {'lines': 'abc'} 400 b'{"lines":[{},{},{}]}'
PROBE {'lines': {'a': 1}} 400 b'{"lines":[{}]}'
```
Los casos con lista (`[5]`, falta `quantity`, `quantity: null`) sí devuelven mensajes correctos. Requiere administrador autenticado; sin fuga ni corrupción de datos.
