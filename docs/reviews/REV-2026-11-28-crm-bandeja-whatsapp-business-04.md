# REV-2026-11-28-crm-bandeja-whatsapp-business-04: Actualización lectura-modificación-escritura de la conversación puede pisar campos concurrentes

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-28-crm-bandeja-whatsapp-business.md (v1)
**Spec reference:** INV-07 («Nunca se pisa un vínculo manual»); PLAN Edge case «Dos usuarios asignan a la vez»
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
DjangoConversationRepository.save (messaging/infrastructure/django/repositories.py) hace UPDATE de last_inbound_at, owner_id, customer_id, lead_id y opportunity_id con los valores leídos antes. assign / link_contact / link_opportunity y el autovínculo (InboxService.auto_link: lee y luego link) son lectura-modificación-escritura sin bloqueo ni UPDATE parcial.

## Expected behavior
Cada operación actualiza solo los campos que cambia (o bloquea la fila con select_for_update), de modo que asignar un responsable no deshaga un autovínculo simultáneo, un vínculo manual no sea pisado por el autovínculo y no se regrese last_inbound_at.

## Actual behavior
Con peticiones concurrentes sobre la misma conversación (p. ej. el worker registra un entrante mientras un usuario asigna), la última escritura sobrescribe también los campos que no tocó, incluida la ventana de 24 h (last_inbound_at). Probabilidad baja; sin prueba.

## Evidence
Lectura de código: `save()` → `.update(last_inbound_at=c.last_inbound_at, owner_id=c.owner_id, customer_id=c.customer_id, lead_id=c.lead_id, opportunity_id=c.opportunity_id)`; `services.assign/link_contact` llaman `_conversation()` y luego `save()` sin transacción de bloqueo. `auto_link` comprueba `conversation.customer_id is None` y luego `inbox.link(...)` en pasos separados.


## Resolution
`save()` solo guarda la ventana y `save_links()` solo responsable/vínculos + prueba.

## Re-verificación (2º Quality Gate)
Parcialmente corregido: `save()` ya solo escribe `last_inbound_at` y `save_links()` solo responsable/vínculos (prueba `test_assigning_does_not_overwrite_the_window...` pasa, pero es secuencial y también pasaba antes del cambio, no ejercita concurrencia). Sin embargo `save_links()` sigue escribiendo los cuatro campos (owner, customer, lead, opportunity) con valores leídos antes: `assign` puede deshacer un vínculo fijado entre su lectura y su escritura, y `InboxService.auto_link` (crm/application/inbox_services.py) lee la conversación, consulta clientes/prospectos y luego llama `inbox.link(..., conversation.opportunity_id)` con la oportunidad leída al inicio: un vínculo manual (contacto u oportunidad) hecho en ese intervalo se pisa, contra INV-07 («nunca se pisa un vínculo manual»). Esperado: UPDATE condicional (p. ej. `filter(customer_id__isnull=True, lead_id__isnull=True)` en el autovínculo) o `select_for_update` en una transacción. Severidad Low (ventana de milisegundos).
