# REV-2026-11-27-crm-integracion-whatsapp-cloud-api-07: El prefijo por empresa solo se valida al guardar; el resolvedor de secretos no lo exige al usar

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-27-crm-integracion-whatsapp-cloud-api.md (v1)
**Spec reference:** INV-05, AC-09 (aislamiento por empresa, REV-01)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`clean_secret_ref` (prefijo + patrón) solo se ejecuta en `ConnectionService.save`. `EnvSecretResolver.available/get` y, con ellos, `ReceiveWebhook`, `gateway_for` y `sync_templates` solo comprueban `SECRET_REF_PATTERN` (`^WHATSAPP_[A-Z0-9_]{1,56}$`). Cualquier fila de `messaging_connection` creada fuera de esa ruta (shell, futuro Django admin, restauración o datos previos a la corrección) puede apuntar a la variable `WHATSAPP_*` de otra empresa y se usará sin objeción. Además, el prefijo son solo 48 bits del UUID (12 hex).

## Expected behavior
Defensa en profundidad: el uso de la referencia verifica también que pertenece a la empresa de la conexión (el puerto `SecretResolver` recibe el prefijo o la conexión lo valida en `ensure_usable`).

## Actual behavior
Una fila con `secret_ref=WHATSAPP_<otra empresa>_TOKEN` es resuelta y usada. Comprobado que la ruta de API sí lo rechaza (pruebas `test_a_company_cannot_use_the_variables_of_another_company` y sondeo manual: minúsculas, vacío tras prefijo, otro prefijo, saltos de línea internos, Unicode y 65 caracteres se rechazan; el espacio/salto de línea en los extremos se recorta).

## Evidence
`backend/modules/messaging/infrastructure/secrets.py`: `SECRET_REF_PATTERN.match(ref)` sin prefijo. `backend/modules/messaging/domain/rules.py::clean_secret_ref` solo se importa desde `application/services.py::ConnectionService.save`.
