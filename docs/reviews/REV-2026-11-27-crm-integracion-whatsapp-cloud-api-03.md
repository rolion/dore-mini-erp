# REV-2026-11-27-crm-integracion-whatsapp-cloud-api-03: Procesamiento de mensaje entrante no es atomico: ventana y evento pueden perderse

**Status:** Closed
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-27-crm-integracion-whatsapp-cloud-api.md (v1)
**Spec reference:** AC-04, AC-10, INV-04
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`ProcessWebhookEvent._inbound` inserta el Message (commit propio en `add_inbound_once`) y despues actualiza `last_inbound_at` y publica `InboundMessageReceived`. El worker no envuelve `run()` en una transaccion y marca el evento `failed` ante cualquier excepcion (sin reintento).

## Expected behavior
Si falla el guardado de la conversacion tras insertar el mensaje, el reproceso debe completar la ventana y publicar el evento (o todo debe ser atomico).

## Actual behavior
Tras un fallo parcial el Message existe pero `last_inbound_at` no se actualiza (ventana cerrada para un cliente que si escribio) y, al reintentar manualmente, `created=False` hace retornar antes de actualizar/publicar: el evento de dominio no se publica nunca. Tambien afecta a un evento `processing` reclamado de nuevo tras 10 min.

## Evidence
Lectura de codigo: `application/services.py::ProcessWebhookEvent._inbound`, `infrastructure/worker.py::process_next_event`, `repositories.py::add_inbound_once`. No hay prueba de fallo parcial.

## Resolución (2026-11-27)
El worker procesa cada evento dentro de `transaction.atomic()` y publica `InboundMessageReceived` solo después de confirmar (`ProcessWebhookEvent.run` devuelve los eventos). Pruebas: `AtomicProcessingTests`.
