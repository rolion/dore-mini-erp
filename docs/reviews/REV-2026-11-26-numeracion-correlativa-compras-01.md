# REV-2026-11-26-numeracion-correlativa-compras-01: La búsqueda de la lista falla con ValueError (500) ante dígitos Unicode no decimales

**Status:** Resolved
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-26-numeracion-correlativa-compras.md (v1)
**Spec reference:** AC-11 (búsqueda de la lista por `NC-000012` o `12`)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build (backend)

## Description
La búsqueda ampliada de la lista de compras decide si el texto es un número con `digits.isdigit()` y luego hace `int(digits)`. `str.isdigit()` es verdadero para caracteres como `²`, `①` o `³` (categoría Unicode «No»), pero `int()` los rechaza.

## Expected behavior
Cualquier texto de búsqueda (hasta `SEARCH_MAX_LENGTH`) devuelve 200 con la lista filtrada (posiblemente vacía); nunca una excepción no controlada. Basta usar `str.isdecimal()` junto con una comprobación ASCII (p. ej. `digits.isascii() and digits.isdigit()`), o capturar `ValueError`.

## Actual behavior
`GET /api/purchases/?q=²` y `?q=nc-²` (y `①`) lanzan `ValueError: invalid literal for int() with base 10` dentro de `DjangoPurchaseRepository` (línea `if digits.isdigit() and int(digits) > 0 and len(digits) <= 9:` de `backend/modules/purchases/infrastructure/django/purchase_repository.py`), que Django responde como HTTP 500. No hay inyección SQL (las consultas usan parámetros y el entero se valida): el defecto es solo la excepción no controlada. La búsqueda de ventas no usa este patrón, así que es una regresión propia de este PR.

## Evidence
Prueba desechable fuera del repositorio (`<scratchpad>/qg_search.py`, subclase de `PurchaseApiTestCase`, ejecutada con `manage.py test qg_search`):

```
Q '²'     EXC ValueError invalid literal for int() with base 10: '²'
Q 'nc-²'  EXC ValueError invalid literal for int() with base 10: '²'
  File ".../purchases/infrastructure/django/purchase_repository.py", line 134, in ...
    if digits.isdigit() and int(digits) > 0 and len(digits) <= 9:
ValueError: invalid literal for int() with base 10: '①'
```
Comprobación aparte: `'²'.isdigit()` → `True`, `'²'.isdecimal()` → `False`, `int('²')` → `ValueError`.
Ninguna prueba del PR cubre una búsqueda con caracteres no ASCII (`test_the_list_search_finds_by_number_code_and_provisional_prefix` solo prueba ASCII).

## Resolución
Resuelto: la búsqueda exige dígitos ASCII (`digits.isascii() and digits.isdigit()`); la prueba `test_the_list_search_ignores_non_ascii_digits_instead_of_failing` (`²`, `nc-²`, `①`, `٣`) reproduce el `ValueError`/500 sin el arreglo (verificado) y pasa con él.
