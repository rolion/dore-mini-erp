# REV-2026-11-27-crm-integracion-whatsapp-cloud-api-05: La publicación de InboundMessageReceived no es durable y su prueba no distingue «tras el commit»

**Status:** Closed
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-27-crm-integracion-whatsapp-cloud-api.md (v1)
**Spec reference:** AC-04, AC-10, INV-04 (residual de REV-03)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
La corrección de REV-03 envuelve `ProcessWebhookEvent.run` en `transaction.atomic()` y publica los eventos de dominio después (`worker.process_next_event`). Quedan dos huecos: (1) la publicación es en memoria y «a lo sumo una vez»: si el proceso muere tras confirmar la transacción y antes de `EventQueue.finish`/`events.publish`, el evento queda `processing`, se reclama a los 10 min, `add_inbound_once` devuelve `created=False` y `_inbound` retorna `None`: el `InboundMessageReceived` de ese mensaje no se publica nunca; igual si un suscriptor lanza (`events.publish` solo lo registra). (2) `test_the_event_is_published_after_the_message_is_committed` corre dentro de `APITestCase` (transacción envolvente que nunca confirma), por lo que pasaría igual si `publish` estuviera dentro del `atomic()`; no prueba «tras el commit».

## Expected behavior
O bien el evento se registra en la misma transacción (outbox/estado en el propio Message) y se reintenta hasta entregarse, o el límite «at-most-once» queda declarado en TASK/ADR; y la prueba debe fallar si la publicación ocurre antes del commit (p. ej. `TransactionTestCase` o `captureOnCommitCallbacks`).

## Actual behavior
Ver Description. Hoy no hay suscriptores (PB-CRM-012/018 pendientes), por eso el impacto es latente.

## Evidence
`backend/modules/messaging/infrastructure/worker.py`: `with transaction.atomic(): published = event_processor(connection).run(payload)` / `EventQueue.finish(...)` / `for event in published: events.publish(event)`. `application/services.py::_inbound`: `if not created: return None`. `application/events.py::publish`: `except Exception: logger.exception(...)`. `tests/test_api.py::AtomicProcessingTests` hereda de `MessagingBase(APITestCase)`.

## Resolución
Se eligió declarar el límite (alternativa permitida): ADR punto 11 documenta que la publicación es en memoria, tras el commit y «a lo sumo una vez», con el outbox como paso previo a que haya suscriptores críticos. La prueba `test_the_event_is_published_after_the_message_is_committed` ahora registra `len(connection.savepoint_ids)` al publicar: valdría 1 si la publicación estuviera dentro del `atomic()` y vale 0 tras el commit.
