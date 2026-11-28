# TASK-crm-bandeja-whatsapp-business: PB-CRM-012 · Bandeja de WhatsApp Business

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** `task/TASK-crm-bandeja-whatsapp-business` (base: `crm`)
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/144
**Fuente:** https://trello.com/c/mkyxOy1O/11-pb-crm-012-bandeja-de-whatsapp-business

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-28 | (nuevo) → INVESTIGATION | Task creado desde tarjeta de Trello | delivery-start |
| 2026-11-28 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | DDR y ADR escritos; decisiones por defecto documentadas | delivery-start |
| 2026-11-28 | PLANNING → ENGINEERING | Plan v1 COMPLETO, Specification READY | delivery-start |
| 2026-11-28 | ENGINEERING → REVIEW | Implementación completa; backend `crm`+`messaging` 231 pruebas OK, frontend Karma/lint/build OK | delivery-build |
| 2026-11-28 | REVIEW → ENGINEERING | Quality Gate FAIL (REV-01 y REV-07 High: pruebas globales de menú y fronteras; REV-02..06 Medium/Low) | delivery-publish |
| 2026-11-28 | ENGINEERING → REVIEW | REV-01..07 corregidos; backend 242 pruebas de crm/messaging/fronteras y Karma completo (2007) OK | delivery-build |

## Investigación

### Requerimiento
Insumo (tarjeta Trello PB-CRM-012, no Specification aprobada): *Como vendedor, quiero atender mensajes entrantes y vincularlos a una oportunidad.* Integrar recepción y envío, asignación de conversaciones y vínculo a contacto y oportunidad; control de acceso y manejo de reintentos. Interfaz: «Seguimiento comercial → Bandeja»: lista de conversaciones, conversación abierta, responsable y acciones para crear o vincular oportunidad. Campos: `Conversation` (`connection_id`, `contact_phone`, `customer_id` o `lead_id`, `owner_id`), `Message` (`provider_message_id` único por conexión, `direction`, `content`, `status`, `sent_at`), relación con oportunidades. Tests: integración (firma incorrecta, evento repetido, estado fuera de orden, adjuntar chat, fallo de envío) y Playwright con proveedor simulado. Depende de PB-CRM-004 (hecho) y PB-CRM-016 (hecho, rama `crm`); habilita PB-CRM-013 y PB-CRM-018 (handoff Bot/Humano).

Aclaración del usuario: «usa la rama crm» → base y destino del PR: `crm` (ya contiene PB-CRM-016 y PB-CRM-004).

### Hechos encontrados
- PB-CRM-016 ya entregó el modelo de la tarjeta bajo otros nombres: `ConversationModel` (`connection`, `phone`, `last_inbound_at`; único por conexión+teléfono) y `MessageModel` (`provider_message_id` único por conexión, `direction`, `type`, `content`, `status`, `sent_at`, `attempts`, `next_attempt_at`, `failure_reason`) en `backend/modules/messaging/infrastructure/django/models.py:51-93`. No tienen `owner_id`, `customer_id`, `lead_id` ni oportunidad.
- Recepción, idempotencia por wamid, estados sin retroceso, firma 401, cola+worker, ventana de 24 h y backoff ya existen y están probados (`backend/modules/messaging/application/services.py:78-233`, `domain/entities.py:61-134`). Esta tarea **no** los reimplementa.
- Reintentos automáticos: `Message.schedule_retry` con backoff exponencial y máximo 5 intentos (`messaging/domain/rules.py:11-13`, `entities.py:127-134`); agotados → `failed` con motivo. No existe reintento manual de un `failed`.
- El evento `InboundMessageReceived` se publica en proceso tras confirmar la transacción y ya prevé que la bandeja (PB-CRM-012) y el asistente (PB-CRM-018) se suscriban (`messaging/application/events.py:1-24`, `domain/events.py`).
- Las vistas de `messaging` no tienen `required_modules` (`api/views.py`, `required_modules = ()`) y no hay fachada pública `services.py` en el módulo; `GET/POST /api/messaging/whatsapp/templates/` ya sirve las plantillas (`api/urls.py`).
- CRM gestiona todo con `required_modules = ('customers',)` (`backend/modules/crm/api/board_views.py:48`), servicios por empresa con repositorios `Django…Repository(company_id)`, puertos en `crm/application/ports.py` y adaptadores que solo hablan con otros módulos por su `services.py` (`crm/infrastructure/adapters.py:1-20`). Puertos ya disponibles: `CustomerGateway.find_active_by_phone/get/create` (`ports.py:61-80`), `UserDirectory.exists/names/search` (`ports.py:107-113`).
- Dominio CRM: `Opportunity` con `lead_id`/`customer_id`/`owner_id` y `attach_customer` (`crm/domain/opportunity.py:66-173`); `Lead` con `normalized_phone` y `converted_customer_id` (`crm/domain/lead.py:40-70`); `Activity` ya admite el canal `whatsapp` (`crm/domain/activity.py:10`); `OpportunityService.create` (`crm/application/opportunity_services.py:115`).
- Permiso por defecto de la API: `CompanyAdminPermission` (usuario autenticado de empresa activa con rol admin) (`backend/modules/accounts/api/permissions.py`); `shared/tenancy.company_id_from(request)` da la empresa.
- Frontend: feature `crm` con rutas `CRM_*_ROUTE` (`features/crm/crm.routes.ts`), servicios `crm-*-api.service.ts`, menú CRM en `assets/data/routes.json:65-125` e i18n `MENUITEMS.CRM.LIST.*` / `CRM.*`; pantalla de WhatsApp en Configuración (`features/settings/pages/whatsapp-integration`, `settings/services/whatsapp-api.service.ts`). No existe plantilla de pantalla «bandeja/chat» en `docs/design/design-system.md`.
- Sin Playwright instalado; las tareas CRM previas se verificaron con Karma por decisión del usuario (TASK-crm-integracion-whatsapp-cloud-api).

### Hipótesis / supuestos no confirmados (decididos por defecto, ver PLAN)
- Control de acceso: todo usuario de la empresa con acceso al módulo Clientes ve **todas** las conversaciones de su empresa y puede (re)asignarlas; no hay roles de vendedor distintos (solo existe `ADMIN`). Nunca se cruzan empresas.
- Vínculo automático por teléfono solo con coincidencia única; con ambigüedad no se vincula (no se adivina).
- Una conversación se vincula a lo sumo a un contacto (cliente **o** prospecto) y a una oportunidad.
- Sin marca de «no leído», sin adjuntos multimedia y sin tiempo real (la pantalla consulta periódicamente): fuera de alcance.

### Módulos y dependencias relacionadas
`messaging` (conversaciones, mensajes, envío), `crm` (oportunidades, prospectos, usuarios; aloja la bandeja), `customers` (vía `CustomerGateway`), `modularity` (módulo `customers`), `shared.tenancy`.

### Implementaciones similares existentes
Pantallas CRM `crm-opportunity-board` (tarjetas + diálogos) y `crm-task-list`; diálogos `opportunity-dialog`, `convert-lead-dialog`; `whatsapp-integration` para plantillas.

### Comportamiento actual
Los mensajes entrantes se guardan pero nadie los ve ni los atiende; no hay responsable ni vínculo con CRM; un mensaje `failed` no se puede reintentar.

### Restricciones
`CLAUDE.md`: `company_id` en todo, dominio sin Django, módulos sin importarse infraestructura, no editar migraciones aplicadas (nueva `0002`), i18n es/en/pt sin texto hardcodeado, Reactive Forms, sin suscripciones colgadas, ruff/flake8 en lo cambiado.

### Riesgos identificados
Acoplamiento `crm`↔`messaging` (mitigado con puerto + fachada, ADR); autovínculo equivocado; el worker y el servidor web son procesos distintos (el suscriptor del evento debe registrarse en ambos); validación real contra Meta pendiente (proveedor simulado en tests).

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — toca dos bounded contexts (`crm` y `messaging`), migración sobre datos existentes, nueva fachada pública y contrato API que consume Angular.

### Diseño requerido
**SI** — pantalla nueva de dos paneles (lista + conversación) con acciones de vínculo, sin plantilla equivalente en el sistema de diseño.

## Diseño
`docs/design/DDR-crm-bandeja-whatsapp-business-bandeja-de-conversaciones.md`. Propone añadir al sistema de diseño la plantilla «Bandeja de conversaciones».

## Arquitectura
`docs/adr/ADR-crm-bandeja-whatsapp-business-bandeja-en-crm-sobre-fachada-de-messaging.md`.

## Plan
`docs/plans/PLAN-2026-11-28-crm-bandeja-whatsapp-business.md` (v1, COMPLETO, READY).

## Implementación
**Backend `messaging`**: migración aditiva `0002_conversation_inbox_links` (owner_id, customer_id, lead_id, opportunity_id + 2 índices; INV-02/03, AC-12); `Conversation.assign/link_contact/link_opportunity` y `Message.requeue()` (INV-08/09); repositorios con página por último mensaje (una consulta + `DISTINCT ON`, sin N+1), hilo con `after`; fachada pública `messaging/services.py` (ADR) que también reexporta sus errores y `subscribe_inbound`.
**Backend `crm`**: puerto `ConversationInbox`, `InboxService` (INV-03…07), `ConversationInboxAdapter` (traduce errores de `messaging` a `CrmNotFound/CrmValidationError/CrmConflict`), API `/api/crm/inbox/…` (API-01…08 + `GET …/opportunities/` para listar las oportunidades vinculables), suscriptor de `InboundMessageReceived` registrado en `CrmConfig.ready()` (autovínculo, AC-08), búsqueda de prospecto por teléfono normalizado.
**Frontend**: `features/crm` — página `crm-inbox` (lista + hilo, consulta cada 10 s con la pestaña visible), diálogos `inbox-contact-dialog` e `inbox-opportunity-dialog`, `crm-inbox-api.service`, ruta `/pocketbiz/crm/inbox`, menú CRM → Bandeja, claves es/en/pt. Pantalla de referencia: lista (`crm-task-list`) y diálogos CRM; plantilla «Bandeja de conversaciones» ya añadida a `design-system.md`.

**Desviaciones respecto al plan**: (1) endpoint extra `GET /api/crm/inbox/conversations/<id>/opportunities/` (necesario para el diálogo, no cambia AC); (2) la asignación se hace con un `<select>` en la cabecera en vez de un diálogo (más simple, mismo contrato); (3) el hilo se recarga completo en cada consulta (los estados de mensajes antiguos cambian, `after` queda disponible en la API pero la UI no lo usa).
**Correcciones tras el Quality Gate**: ver REV-01..07 (menú, fronteras crm→messaging declaradas, prueba de migración con reversa, «Crear prospecto» en el diálogo de contacto —cumple UI-04—, `save()` sin pisar campos concurrentes, pruebas de aislamiento y paginación).
**Deuda técnica**: `crm/infrastructure/inbox_subscriber.py` importa `inbox_views.inbox_service` para armar el servicio (mover el armado a un módulo neutral si crece); sin «no leídos» ni multimedia (fuera de alcance).

**Verificación propia (no es el Quality Gate)**: frontend `ng lint`, `i18n:check` (0 faltantes), `ng build` y 28 pruebas Karma de la bandeja OK; backend `manage.py check`, `makemigrations --check` (sin cambios), ruff/flake8 limpios y pruebas de dominio de `messaging` OK. Pruebas de integración de la bandeja (`crm/tests/test_api_inbox.py`) y suites `crm` + `messaging`: 231 OK.

## Review
**Primer Quality Gate: FAIL** (subagente aislado). Hallazgos: [REV-01](../reviews/REV-2026-11-28-crm-bandeja-whatsapp-business-01.md) High (2 pruebas Karma del menú), [REV-07](../reviews/REV-2026-11-28-crm-bandeja-whatsapp-business-07.md) High (2 pruebas de fronteras de módulos), REV-02 y REV-03 Medium, REV-04..06 Low. Corregidos todos; REV-06 se resuelve documentando el alcance (abajo). Pendiente: segundo Quality Gate.
Alcance aclarado (REV-06): las plantillas se envían sin variables (`components` vacío) y el hilo muestra los 200 mensajes más recientes.

## Publicación
_Pendiente_
