# REV-2026-11-27-crm-integracion-whatsapp-cloud-api-02: Evento firmado de conexion disabled responde 401 en vez de ignorarse (sin prueba)

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-27-crm-integracion-whatsapp-cloud-api.md (v1)
**Spec reference:** Edge cases: «evento de una conexion disabled -> ignorado»; API-02
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`ConnectionDirectory.by_phone_number_id` excluye las conexiones `disabled`; `ReceiveWebhook.handle` trata la ausencia como `InvalidSignature`. Ademas, si falta la variable del App Secret responde 503 (distinguible de 401 para un llamador sin firma).

## Expected behavior
Un evento valido de una conexion deshabilitada se acepta con 200 sin efecto (evita reintentos de Meta y que desactive el webhook); no debe haber prueba faltante para este caso del PLAN.

## Actual behavior
Responde 401 y no hay prueba del caso. Hoy ninguna ruta de la API pone una conexion en `disabled`, por lo que es latente. El 503 por secreto ausente revela, sin firma valida, que existe una conexion para ese phone_number_id.

## Evidence
Lectura de codigo: `infrastructure/django/repositories.py::ConnectionDirectory.by_phone_number_id`, `application/services.py::ReceiveWebhook.handle`, `api/views.py::WhatsAppWebhookView.post`. grep de tests en `modules/messaging/tests/test_api.py`: sin caso de conexion disabled.
