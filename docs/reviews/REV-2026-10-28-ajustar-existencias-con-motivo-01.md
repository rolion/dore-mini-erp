# REV-2026-10-28-ajustar-existencias-con-motivo-01: Cantidad contada o saldo esperado enormes provocan 500 en lugar de 400

**Status:** Resolved (verificado en el ciclo 2)
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-28-ajustar-existencias-con-motivo.md (v1)
**Spec reference:** EDGE-02 (valores inválidos => 400 por campo), INV-05, AC-01
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`validate_counted_quantity` y `validate_expected_balance` (`backend/modules/inventory/domain/adjustment.py`) llaman a `Decimal.quantize(...)` sobre el valor recibido. Con valores de mas de ~28 digitos significativos (o exponentes enormes en `expected_system_quantity`) `quantize` lanza `decimal.InvalidOperation`, que no se captura: solo se captura al construir el `Decimal`. `ConfirmAdjustment._validate` solo atrapa `AdjustmentValidationError`, y la vista tampoco lo mapea, asi que `POST /api/stock-adjustments/` responde 500.

## Expected behavior
Cualquier valor numerico fuera de rango responde 400 con el error del campo (`counted_quantity` o `expected_system_quantity`), nunca 500 (EDGE-02).

## Actual behavior
Se levanta `InvalidOperation` no controlada (500) con `counted_quantity` de 31 digitos, o con `expected_system_quantity` = "1e30", "1e999999" o 29 digitos. El tope `COUNTED_MAX` nunca se alcanza porque `quantize` falla antes.

## Evidence
```
validate_counted_quantity('1' + '0'*30)                    -> InvalidOperation
validate_counted_quantity('99999999999999999999999999999.5') -> InvalidOperation
validate_expected_balance('1e30')                           -> InvalidOperation [<class 'decimal.InvalidOperation'>]
validate_expected_balance('1e999999')                       -> InvalidOperation
validate_expected_balance('12345678901234567890123456789')  -> InvalidOperation
```
(ejecutado con `DJANGO_SETTINGS_MODULE=config.settings.test python -c ...` desde `backend/`). Sugerencia: comparar contra `COUNTED_MAX`/un tope de saldo antes de `quantize`, o capturar `InvalidOperation` alrededor del `quantize`, y agregar tests.
