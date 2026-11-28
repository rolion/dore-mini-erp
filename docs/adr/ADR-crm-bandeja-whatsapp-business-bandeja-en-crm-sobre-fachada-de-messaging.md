# ADR-crm-bandeja-whatsapp-business-bandeja-en-crm-sobre-fachada-de-messaging: La bandeja vive en `crm` y usa `messaging` por una fachada

**Estado:** Propuesto
**Task relacionado:** TASK-crm-bandeja-whatsapp-business
**Fecha:** 2026-11-28

## Contexto
La tarjeta pide asignar conversaciones y vincularlas a contacto y oportunidad. Las conversaciones y mensajes ya viven en `messaging` (PB-CRM-016), que por ADR previo no importa módulos de negocio. Contacto, prospecto, oportunidad y usuarios responsables son conceptos de `crm`. `docs/architecture/ddd.md`: los módulos no se importan infraestructura entre sí; el dominio no importa Django.

## Decisión
1. **Datos**: `messaging_conversation` gana columnas opacas y nulas `owner_id` (entero, usuario de la empresa), `customer_id`, `lead_id`, `opportunity_id` (UUID), **sin claves foráneas** a otros módulos, con índices `(company_id, owner_id)` y `(company_id, opportunity_id)`. `messaging` solo guarda y devuelve esos valores (métodos `assign`, `link_contact`, `link_opportunity` del agregado `Conversation`); no sabe qué significan.
2. **Reglas del vínculo en `crm`**: un nuevo servicio `InboxService` (`crm/application/inbox_services.py`) valida que usuario, cliente, prospecto y oportunidad existan en la empresa y sean coherentes entre sí (INV del PLAN), y orquesta crear/vincular oportunidad reutilizando `OpportunityService`.
3. **Puerto/adaptador**: `crm/application/ports.py` define `ConversationInbox`; su adaptador (`crm/infrastructure/adapters.py`) llama solo a una **fachada pública nueva `modules/messaging/services.py`** (listar/leer conversaciones y mensajes, enviar texto/plantilla, reencolar un `failed`, asignar y vincular). `crm` nunca importa `messaging.infrastructure` ni sus modelos.
4. **API** bajo `/api/crm/inbox/…` (mismo permiso y `required_modules = ('customers',)` que el resto de CRM). Las rutas de `messaging` (webhook, conexión, plantillas) no cambian.
5. **Autovínculo**: `crm` se suscribe a `InboundMessageReceived` (`messaging.application.events.subscribe`) en `CrmConfig.ready()`; así queda registrado también en el proceso del worker (`run_messaging_worker`), donde se publica el evento. Un fallo del suscriptor no pierde el mensaje (ya garantizado por `publish`).
6. **Reintento manual**: `Message.requeue()` (solo `failed` saliente) en el dominio de `messaging`; el envío sigue siendo asíncrono por el worker existente.

## Alternativas consideradas
- **Bandeja dentro de `messaging` con FKs a CRM**: rompe el límite de contextos y obliga a `messaging` a importar `crm`. Descartada.
- **Tabla de vínculos en `crm` (`ConversationLink`)**: aísla del todo, pero duplica la clave de conversación y obliga a joins entre contextos para listar con filtros por responsable. Más piezas que el beneficio. Descartada; las columnas opacas son simples y reversibles.
- **Servidor de eventos/WebSockets para tiempo real**: fuera del MVP (CLAUDE.md: sin infraestructura nueva); se usa consulta periódica.

## Estrategia de rollback / mitigación
Migración `messaging 0002` **aditiva** (4 columnas nulas + 2 índices): no reescribe filas ni toca datos existentes. Rollback: revertir el despliegue y `migrate messaging 0001` (elimina solo las columnas nuevas; las conversaciones y mensajes quedan intactos). El autovínculo y los endpoints nuevos no afectan a webhook ni worker si fallan (el suscriptor está aislado por `publish`).

## Consecuencias
- `messaging` gana una fachada pública y `crm` un adaptador más; los otros módulos (PB-CRM-013/018) pueden reutilizar la fachada.
- Los identificadores vinculados pueden quedar colgando si se borra un cliente/oportunidad; la lectura debe tolerarlo (mostrar «no disponible») y no fallar.
- El suscriptor en proceso es «a lo sumo una vez»: si el proceso cae justo tras confirmar, ese mensaje no se autovincula (queda sin vincular; se vincula a mano).
