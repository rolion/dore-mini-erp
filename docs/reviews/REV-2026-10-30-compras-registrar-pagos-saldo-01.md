# REV-2026-10-30-compras-registrar-pagos-saldo-01: Los errores de forma (payment_id, payment_date) no se devuelven junto con los errores de dominio

**Status:** Fixed
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-30-compras-registrar-pagos-saldo.md (v1)
**Spec reference:** AC-04 («todos los errores de campos se devuelven juntos»)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`PaymentInputSerializer` valida `payment_id` (UUID), `payment_date` (formato) y el tipo de `amount`/`payment_method` antes de llamar al dominio. Si falla la forma de algún campo, la vista responde 400 solo con esos errores y nunca ejecuta `Purchase.register_payment`, de modo que los errores de dominio de los demás campos (monto 0, método inválido, sobrepago) no se informan en la misma respuesta.

## Expected behavior
AC-04: método ausente o fuera del catálogo, fecha ausente, inválida o futura y monto inválido se devuelven juntos en un único 400 por campo.

## Actual behavior
Con fecha mal formada el 400 solo contiene `payment_date`; el monto 0 y el método inválido quedan ocultos hasta corregirla. Lo mismo ocurre con un `payment_id` faltante/no UUID (solo `payment_id`). El caso con fecha sintácticamente válida pero futura sí se devuelve junto (cubierto por `test_method_and_date_are_validated_together`); el caso de formato inválido no tiene prueba.

## Evidence
Servidor local (BD de desarrollo), POST `/api/purchases/{id}/payments/`:
```
body {"payment_id":"<uuid>","amount":"0","payment_method":"X","payment_date":"abc"}
-> {"payment_date":["Fecha con formato erróneo. Use uno de los siguientes formatos en su lugar: YYYY-MM-DD."]} [400]
body {}
-> {"payment_id":["Este campo es requerido."]} [400]
```
Impacto bajo: la interfaz envía fechas de `input type=date` y valida en cliente.

## Resolución
Corregido: `PaymentInputSerializer` solo valida `payment_id`; `amount` y `payment_method` pasan sin validar al dominio (`RawField`) y la fecha mal formada llega como valor inválido (`LenientDateField`), de modo que el dominio devuelve juntos los errores de monto, método y fecha. `payment_id` faltante o no UUID sigue respondiendo solo por ese campo: es la clave de idempotencia, no un campo del formulario. Prueba: `test_malformed_shapes_are_reported_together_with_domain_errors`.
