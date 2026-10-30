# REV-2026-10-29-catalogo-usos-del-producto-02: Precio inválido oculto bloquea el guardado sin mensaje visible

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-29-catalogo-usos-del-producto.md (v1)
**Spec reference:** UI-01 (precio visible solo con «Se puede vender»), UI-06 (errores por campo); DDR: «al apagarlo el campo se oculta sin borrar lo escrito»
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Al apagar «Se puede vender» el campo `salePrice` se oculta con `@if`, pero conserva el valor escrito y el validador `Validators.pattern(PRICE_PATTERN)`; solo se quita `required`.

## Expected behavior
Un campo oculto no debe impedir guardar un producto no vendible, o su error debe ser visible.

## Actual behavior
Si el usuario escribió un precio inválido (p. ej. «abc»), apaga «Se puede vender» y guarda, `form.invalid` es verdadero, `onSubmit` retorna sin enviar y no hay ningún mensaje visible (el campo está oculto). Caso de borde poco probable.

## Evidence
- `product-form.component.ts`: `salePrice: ['', [Validators.required, Validators.pattern(PRICE_PATTERN)]]`; el suscriptor de `canSell` solo hace `removeValidators(Validators.required)`; `onSubmit` hace `if (this.form.invalid || this.saving) { markAllAsTouched(); return; }`.
- Revisión por código; no ejercido en navegador.
