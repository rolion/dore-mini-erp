# REV-2026-10-30-compras-registrar-pagos-saldo-03: Casos límite de la spec sin prueba (EDGE-07, EDGE-08, formato de monto exponencial) y a11y de errores del diálogo

**Status:** Fixed
**Severity:** Low
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-10-30-compras-registrar-pagos-saldo.md (v1)
**Spec reference:** EDGE-07, EDGE-08, EDGE-04; design-system §7 (accesibilidad mínima)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
1. EDGE-07 (proveedor o producto desactivado después de confirmar → se puede pagar) y EDGE-08 (compra confirmada antes de esta task → `paid_total 0.00`, `balance = total`, `unpaid`) figuran en la Specification y no tienen prueba que los ejercite (`grep` de EDGE-07/EDGE-08, `active=False` o desactivar en `test_payment_*.py` sin resultados). El comportamiento sí es correcto (verificado a mano para EDGE-08 en una compra recién confirmada; EDGE-07 por lectura: `register_payment` no consulta proveedor ni productos).
2. EDGE-04 menciona montos no numéricos; el código rechaza `'1e3'`, `NaN`, `Infinity` (verificado en vivo, 400) pero la lista de `test_invalid_amounts_are_rejected` no incluye estos valores.
3. Accesibilidad (design-system §7): en `payment-dialog.component.html` los mensajes de error `small.text-danger` no están asociados a su campo (`aria-describedby`/`aria-invalid`) ni anunciados (`role="alert"` solo en el error general).

## Expected behavior
Cada EDGE de la Specification con una verificación; errores de formulario asociados programáticamente al campo.

## Actual behavior
Ver Description.

## Evidence
- `grep -n "EDGE-07\|EDGE-08\|deactivate\|inactive\|active=False" backend/modules/purchases/tests/test_payment_*.py` → sin salida.
- Servidor local: `amount:"1e3"` → `{"amount":["El monto debe ser un número decimal."]} [400]`; `"NaN"` y `"Infinity"` igual; `10.5` (float JSON) y `true` → `{"amount":["Debe ser un número decimal enviado como texto."]} [400]`.
- `grep -n "aria-" payment-dialog.component.html` → solo `aria-label="Cerrar"`.

## Resolución
Corregido: pruebas de EDGE-07 (proveedor/producto desactivados), EDGE-08 (compra sin pagos previos) y montos `1e3`, `NaN`, `Infinity`, lista y objeto; errores del diálogo con `id`, `role="alert"`, `aria-invalid` y `aria-describedby`. Pruebas: `test_a_deactivated_supplier_or_product_does_not_block_payment`, `test_a_purchase_confirmed_before_payments_existed_starts_unpaid`, `test_invalid_amounts_are_rejected` y el spec del diálogo.
