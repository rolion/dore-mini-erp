# REV-2026-10-29-compras-borrador-crear-editar-02: cantidades o precios con muchos dígitos provocan decimal.InvalidOperation (500)

**Status:** Fixed (pendiente de reverificar en el ciclo 2)
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-29-compras-borrador-crear-editar.md (v1)
**Spec reference:** AC-03 (cantidad > máximo → 400 con error por línea), AC-04 (valores no válidos → error de campo de su línea), INV-04, EDGE-06 («no 500»)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`validate_quantity` y `validate_unit_price` (`backend/modules/purchases/domain/purchase.py`) hacen `quantity.quantize(Decimal('0.001'))` (y `parse_money` hace lo propio) sobre el valor tal como llegó. Con más dígitos enteros que la precisión del contexto Decimal (28 por defecto), `quantize` lanza `decimal.InvalidOperation`. Esa excepción no es `PurchaseValidationError`, no se captura en `application` ni en `_run` (`api/purchase_views.py` solo traduce `PurchaseValidationError`, `PurchaseNotFound` y `PurchaseNotEditable`), así que subiría como 500. `DecimalInputField` solo comprueba el tipo (str o int) y el formulario Angular tampoco limita la longitud.

## Expected behavior
Un importe o cantidad enorme (p. ej. 40 dígitos, o un entero JSON muy grande) devuelve 400 con `items: [{"quantity": ["La cantidad no puede superar 99999999.999."]}]` (o el equivalente de `unit_price`), y no se persiste nada.

## Actual behavior
Se lanza `decimal.InvalidOperation` no controlado (500).

## Evidence
Ejecución real de las funciones del dominio (`DJANGO_SETTINGS_MODULE=config.settings.test`):
```
validate_quantity   '1'*40        -> InvalidOperation
validate_unit_price '1'*40        -> InvalidOperation
validate_quantity   10**40 (int)  -> InvalidOperation
validate_unit_price 10**40 (int)  -> InvalidOperation
validate_quantity   '1'*40+'.5'   -> InvalidOperation
```
(con decimales largos, `'0.'+'1'*40`, sí responde bien: «admite como máximo 3 decimales»). No se ejecutó la llamada HTTP completa; que llegue como 500 se deduce de la lectura del código (`_run` no captura esa excepción).

Corrección sugerida: comparar con `QUANTITY_MAX`/`MONEY_MAX` antes de `quantize`, o capturar `InvalidOperation` como error del campo; añadir pruebas de dominio y de API para estos casos.
