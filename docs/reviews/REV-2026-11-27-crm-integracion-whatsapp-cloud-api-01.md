# REV-2026-11-27-crm-integracion-whatsapp-cloud-api-01: secret_ref puede apuntar a la variable WHATSAPP_* de otra empresa

**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-27-crm-integracion-whatsapp-cloud-api.md (v1)
**Spec reference:** INV-05, AC-09, Authorization (aislamiento por empresa)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
La validacion de `secret_ref`/`app_secret_ref` solo exige el patron `WHATSAPP_*` (`domain/rules.py::clean_secret_ref`). Todas las empresas comparten el mismo espacio de nombres de variables de entorno del servidor y no hay unicidad ni propiedad de la referencia por empresa (`ConnectionModel.secret_ref` sin restriccion). Ademas, `ConnectionService.save` usa `EnvSecretResolver.available`, de modo que el estado resultante (`active` vs `pending/secrets_missing`) revela si una variable con ese nombre existe.

## Expected behavior
Una empresa no debe poder usar (ni detectar) el token o App Secret configurado para otra empresa; el aislamiento por company_id debe cubrir tambien las referencias a secretos (por ejemplo, referencia unica por empresa o prefijo derivado de la empresa).

## Actual behavior
Un administrador de la empresa A puede guardar `secret_ref=WHATSAPP_TOKEN_EMPRESA2` y su conexion queda `active`; con ese token puede listar plantillas de la WABA de B (`waba_id` de B) y enviar con cualquier `phone_number_id` del mismo token aun no conectado. Tambien puede enumerar nombres de variables existentes por el estado devuelto. Requiere conocer el nombre de la variable ajena.

## Evidence
Lectura de codigo: `backend/modules/messaging/domain/rules.py` (SECRET_REF_PATTERN, clean_secret_ref), `application/services.py::ConnectionService.save`, `infrastructure/django/models.py::ConnectionModel` (sin unique en secret_ref/app_secret_ref). Prueba existente solo cubre refs sin prefijo WHATSAPP_ (`test_rejects_refs_that_could_leak_server_secrets`); ninguna cubre refs compartidas entre empresas.
