# REV-2026-11-17-registrar-gastos-cuenta-gasto-pago-03: posting-options: parametro payment_method sin limite de longitud y sin prueba de aislamiento de categoria ajena

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-17-registrar-gastos-cuenta-gasto-pago.md (v1)
**Spec reference:** API-02, AC-11; Non-functional (validacion/DoS)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`PostingOptionsQuerySerializer.payment_method` es un `CharField` sin `max_length` y el endpoint devuelve todas las cuentas elegibles de la empresa. No se encontro fuga ni fallo, pero falta acotar la entrada y probar con dos empresas que una `category_id` ajena no se resuelve.

## Expected behavior
`payment_method` acotado (p. ej. `max_length` del codigo de metodo) y una prueba de aislamiento para `category_id` de otra empresa en `posting-options`.

## Actual behavior
Con `payment_method` de 100000 caracteres responde 200 sin error; con una categoria de otra empresa se ignora (issues `category_required`, sin datos ajenos). Correcto pero sin cota ni prueba automatizada.

## Evidence
- `backend/modules/expenses/api/serializers.py` (`PostingOptionsQuerySerializer`).
- Sonda: `OPT-LONG 200 ...`; `OPT-FOREIGN 200 {"covered":true,...,"expense_account":null,...,"category_required"...}`.
