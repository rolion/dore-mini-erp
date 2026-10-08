# REV-2026-10-08-clientes-mvp-02: AC-02 no se cumple cuando `name` es inválido junto con otros campos (errores no se devuelven juntos)

**Status:** Closed (verificado en re-review sobre 58e1784)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-08-clientes-mvp.md (v1)
**Spec reference:** AC-02 ("Los errores de varios campos se devuelven juntos")
**Plan mode:** COMPLETO
**Suggested owner:** delivery-engineer

## Description
`CustomerInputSerializer` declara `name = CharField(max_length=150)` (no vacío por defecto). Si `name` viene vacío/en blanco o de más de 150 caracteres, el serializer falla primero y responde solo el error de `name`; las validaciones de dominio de `phone`, `email` y `notes` no llegan a ejecutarse, así que el cliente no recibe todos los errores a la vez. El test `test_invalid_email_phone_notes_report_all_errors_together` no incluye un `name` inválido.

## Expected behavior
AC-02: nombre inválido + correo/teléfono/notas inválidos → un solo 400 con los errores de todos los campos.

## Actual behavior
Solo se informa el error de `name`.

## Evidence
```
POST /api/customers/ {"name":"","email":"bad","phone":"1234567890123456789012345678901"}
-> 400 {"name":["Este campo no puede estar en blanco."]}

POST /api/customers/ {"name":"ok","email":"bad","phone":"<31 caracteres>","notes":"x"}
-> 400 {"phone":["El teléfono no puede superar 30 caracteres."],"email":["Ingresa un correo válido."]}
```
Además el mensaje de `name` es el genérico de DRF y no el del dominio ("El nombre es obligatorio.").

## Required action
Dejar `name` como `CharField(required=False/allow_blank=True)` sin `max_length` en el serializer (solo forma y tipo) y delegar longitud/obligatoriedad al dominio, o fusionar los errores del serializer con los del dominio; agregar un test con `name` inválido + otros campos. Impacto bajo: el formulario valida en cliente antes de enviar.
