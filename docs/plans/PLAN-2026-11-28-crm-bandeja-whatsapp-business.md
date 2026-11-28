# PLAN-2026-11-28-crm-bandeja-whatsapp-business (v1)

**Task:** TASK-crm-bandeja-whatsapp-business · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-crm-bandeja-whatsapp-business-bandeja-de-conversaciones / ADR-crm-bandeja-whatsapp-business-bandeja-en-crm-sobre-fachada-de-messaging

## Objective
Que el vendedor atienda desde CRM las conversaciones de WhatsApp: verlas, responder (texto o plantilla), reintentar envíos fallidos, asignarlas a un responsable y vincularlas a un contacto (cliente o prospecto) y a una oportunidad, existente o nueva.

## Context
Resumen en `docs/tasks/TASK-crm-bandeja-whatsapp-business.md`. Base y destino del PR: rama `crm` (ya incluye PB-CRM-016 y PB-CRM-004). La recepción, firma, idempotencia por wamid, estados sin retroceso, ventana de 24 h y backoff automático ya existen en `messaging` y no se reimplementan.

# Specification

## Domain context
`crm` aloja la bandeja y las reglas de vínculo; `messaging` guarda conversaciones/mensajes y expone una fachada; `customers` solo se consulta por `CustomerGateway`. Ver ADR.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Bandeja | Lista de conversaciones de WhatsApp de la empresa y su hilo | Tarjeta |
| Conversación | Hilo con un teléfono de la conexión (`messaging_conversation`) | PB-CRM-016 |
| Responsable (`owner_id`) | Usuario de la empresa que atiende la conversación; puede no haber | Tarjeta |
| Contacto vinculado | Cliente (`customer_id`) **o** prospecto (`lead_id`) de la conversación | Tarjeta |
| Oportunidad vinculada | Oportunidad CRM asociada a la conversación («adjuntar chat») | Tarjeta |
| Ventana abierta | Último mensaje entrante hace ≤ 24 h: permite texto libre | PB-CRM-016 |

## Current behavior
Ver TASK (Hechos). Los mensajes entrantes quedan guardados sin responsable ni vínculos; no hay bandeja ni reintento manual.

## Expected behavior
La bandeja lista y abre conversaciones; permite responder, reenviar un mensaje fallido, asignar y vincular; los mensajes entrantes de teléfonos con un único cliente (o prospecto) coincidente se vinculan solos.

## Domain rules / invariants
- **INV-01** (existente, INV-01 de PB-CRM-016) Toda fila lleva `company_id`; toda consulta de la bandeja filtra por la empresa del usuario; conversaciones de otra empresa responden 404.
- **INV-02** `owner_id` es `NULL` o un usuario de la misma empresa.
- **INV-03** Una conversación tiene a lo sumo **un** contacto: `customer_id` XOR `lead_id` (o ninguno). Vincular uno reemplaza al otro.
- **INV-04** `customer_id`/`lead_id` existen en la empresa; el cliente debe estar activo para vincularlo.
- **INV-05** `opportunity_id` es una oportunidad **abierta** de la empresa cuyo contacto coincide con el de la conversación (mismo `customer_id`, o mismo `lead_id`, o la oportunidad de un prospecto ya convertido a ese cliente). Si la conversación no tiene contacto, al vincular la oportunidad hereda el de la oportunidad (cliente si lo tiene; si no, prospecto). Contacto distinto → 409 `contact_mismatch`.
- **INV-06** Al cambiar o quitar el contacto, si la oportunidad vinculada ya no corresponde al nuevo contacto se desvincula.
- **INV-07** Autovínculo al recibir un mensaje: solo si la conversación no tiene contacto; con **exactamente un** cliente activo con ese teléfono normalizado se vincula; si hay 0, con **exactamente un** prospecto no convertido; si hay más de uno en el nivel, no se vincula. Nunca se pisa un vínculo manual.
- **INV-08** Reintento manual: solo mensajes salientes `failed`; vuelve a `queued` con intentos en 0 y el worker lo entrega. Texto/interactivo con ventana cerrada → `WindowClosed` (409). Un mensaje no `failed` → 409 `not_retryable`.
- **INV-09** Estados de `Message` solo cambian por métodos del agregado (`requeue()`), nunca por asignación; los vínculos de `Conversation` por `assign`, `link_contact`, `link_opportunity`.
- **INV-10** Responder reutiliza `SendMessages` (ventana, plantilla aprobada, conexión activa) sin saltarse sus reglas.

## Acceptance criteria
- **AC-01** `GET /api/crm/inbox/conversations/` lista las conversaciones de la empresa ordenadas por último mensaje (más reciente primero), con teléfono, contacto, responsable, oportunidad, vista previa del último mensaje y `window_open`; filtros `scope=mine|unassigned|all`, `search` (teléfono o nombre del contacto), `opportunity_id`; paginado.
- **AC-02** `GET …/conversations/<id>/` y `…/messages/` devuelven el hilo en orden cronológico con `status`, `direction`, `type`, contenido y `failure_reason`; `after=<fecha>` devuelve solo los más nuevos (para actualización periódica).
- **AC-03** Responder con texto crea un mensaje saliente `queued` (202) si la ventana está abierta; con ventana cerrada → 409 `window_closed`; con plantilla aprobada se envía aunque la ventana esté cerrada; plantilla no aprobada → 409.
- **AC-04** Un fallo de envío (rechazo permanente o backoff agotado) deja el mensaje `failed` con motivo visible; `POST …/messages/<id>/retry/` lo reencola (INV-08).
- **AC-05** `PUT …/conversations/<id>/owner/` asigna o desasigna (`owner_id` nulo) a un usuario de la empresa; usuario ajeno → 400.
- **AC-06** `PUT …/contact/` vincula cliente o prospecto (INV-03/04) o lo quita; uno inexistente o de otra empresa → 400/404.
- **AC-07** `PUT …/opportunity/` vincula una oportunidad abierta coherente con el contacto (INV-05) o la quita; `POST …/opportunity/` crea una oportunidad para el contacto de la conversación (tablero/título/monto como en `POST /api/crm/opportunities/`) y la vincula en una sola operación; sin contacto vinculado → 400 «vincula primero un contacto».
- **AC-08** Autovínculo por teléfono (INV-07) al publicarse `InboundMessageReceived`, sin pisar vínculos manuales; ambigüedad → sin vincular.
- **AC-09** Un mensaje entrante repetido (mismo wamid), con firma inválida o con estados fuera de orden no altera la bandeja (regresión de PB-CRM-016 ejercida a través de la bandeja).
- **AC-10** Aislamiento y acceso: sin sesión → 401; módulo `customers` deshabilitado → 403 con el mensaje estándar; conversación/oportunidad/cliente de otra empresa nunca visible ni modificable.
- **AC-11** Interfaz (DDR): menú **CRM → Bandeja**, lista + hilo, filtros, responder (texto/plantilla), reenviar, asignar, vincular contacto, vincular/crear oportunidad, estados vacío/cargando/error, responsive y textos es/en/pt.
- **AC-12** Migración aditiva `messaging 0002` aplicable sobre datos existentes sin perderlos (conversaciones previas quedan sin responsable ni vínculos).

## Edge cases / Error cases
- Cliente/oportunidad vinculados que luego se borran o desactivan: la lectura muestra «No disponible» sin error 500.
- Prospecto convertido después de vincular: la conversación sigue con `lead_id`; la vista muestra el cliente convertido como contacto.
- Dos usuarios asignan a la vez: gana la última escritura (sin historial).
- Conexión deshabilitada o en error: la lista sigue visible; responder → 409 `connection_not_active`.
- Mensaje entrante de tipo no texto (imagen, audio…): se muestra como «[Imagen]» etc.; el contenido multimedia no se descarga.
- Teléfono del contacto con formato distinto: la comparación usa el teléfono normalizado (INV-06 de PB-CRM-016).

## Authorization / permissions
Mismo permiso que CRM (usuario autenticado de empresa activa, `CompanyAdminPermission`) y `required_modules = ('customers',)`. La empresa sale del usuario (`shared/tenancy`), nunca del cliente. Todos los usuarios de la empresa ven todas las conversaciones y pueden reasignarlas (decisión por defecto; no hay roles de vendedor). Una restricción «solo ver lo mío» exigiría roles y es una evolución futura.

## API contract
Prefijo `/api/crm/inbox/` (compatible hacia atrás: no cambia ninguna ruta existente).
- **API-01** `GET conversations/?scope&search&opportunity_id&page` → `{count,next,previous,results:[{id,phone,contact:{type,id,name}|null,owner:{id,name}|null,opportunity:{id,title}|null,last_message:{type,preview,direction,status,at}|null,window_open,window_expires_at}]}`.
- **API-02** `GET conversations/<id>/` → igual a un resultado + `connection_active`.
- **API-03** `GET conversations/<id>/messages/?after=<ISO>` → `{results:[{id,direction,type,content,status,failure_reason,created_at,sent_at}]}`.
- **API-04** `POST conversations/<id>/messages/` `{type:'text',body}` o `{type:'template',template_id,components?}` → 202 con el mensaje; errores 400/409 con `code`.
- **API-05** `POST conversations/<id>/messages/<mid>/retry/` → 202.
- **API-06** `PUT conversations/<id>/owner/` `{owner_id:int|null}`.
- **API-07** `PUT conversations/<id>/contact/` `{customer_id}` | `{lead_id}` | `{}` (quitar).
- **API-08** `PUT conversations/<id>/opportunity/` `{opportunity_id:uuid|null}`; `POST conversations/<id>/opportunity/` `{board_id,title,amount,stage_id?,owner_id?}` → 201 con la conversación.
- Las plantillas aprobadas se leen de `GET /api/messaging/whatsapp/templates/` (existente).

## UI behavior
- **UI-01** Ruta `/pocketbiz/crm/inbox`, menú CRM → Bandeja, plantilla «Bandeja de conversaciones» (DDR, a añadir a `design-system.md`).
- **UI-02** Panel izquierdo: filtros Mías/Sin asignar/Todas, búsqueda, filas con vista previa, responsable y «Ventana cerrada».
- **UI-03** Panel derecho: cabecera con contacto/responsable/oportunidad y acciones; burbujas con estado; «Falló» + Reenviar; caja de respuesta con texto o plantilla según ventana.
- **UI-04** Diálogos Asignar, Vincular contacto (cliente/prospecto/crear prospecto), Vincular o crear oportunidad (Reactive Forms con `[formGroup]`).
- **UI-05** Consulta periódica de mensajes nuevos cada 10 s con la pestaña visible; limpieza al destruir el componente.
- **UI-06** < 992 px un panel a la vez con «Volver a la lista».
- **UI-07** Estados cargando/vacío/error/éxito; sin conexión activa → aviso con enlace a Configuración → WhatsApp; todos los textos con `translate` y claves en `es/en/pt`.

## Non-functional requirements
Consultas de lista con una sola consulta de «último mensaje» por página (sin N+1); índices `(company_id, owner_id)` y `(company_id, opportunity_id)`; sin secretos ni contenido de mensajes en logs.

## Out of scope
Marca de no leído y contadores; adjuntos/multimedia; tiempo real (WebSockets); historial de asignaciones; reglas de reparto automático; roles «solo ver lo mío»; campañas (PB-CRM-013) y asistente/handoff (PB-CRM-018); mostrar el chat dentro del Kanban de oportunidades; registrar automáticamente una `Activity` por mensaje.

## Open questions
Ninguna bloqueante. Las decisiones por defecto (visibilidad total, autovínculo solo con coincidencia única, un contacto y una oportunidad por conversación) pueden cambiarse sin migración.

# Test Specification

## Unit tests
- Dominio `messaging`: `Conversation.assign/link_contact/link_opportunity`; `Message.requeue()` (solo `failed`, reinicia intentos) — INV-08/09.
- Dominio/servicio `crm`: reglas INV-03, 05, 06, 07 del `InboxService` con repositorios en memoria.

## Integration tests
API con proveedor simulado (`MESSAGING_PROVIDER=fake`) y base de datos de pruebas, dos empresas:
- Listado, filtros, búsqueda, paginado y vista previa; orden por último mensaje (AC-01).
- Hilo y `after` (AC-02).
- Responder dentro/fuera de ventana, plantilla aprobada/no aprobada (AC-03).
- **Fallo de envío**: pasarela falsa que rechaza → `failed` con motivo; reintento → `queued` → entregado (AC-04).
- Asignar/desasignar, usuario ajeno (AC-05); vincular/quitar contacto (AC-06); **adjuntar chat**: vincular, crear y desvincular oportunidad, contacto incompatible (AC-07).
- Autovínculo: único cliente, único prospecto, ambiguo, no pisa manual (AC-08).
- **Firma incorrecta, evento repetido, estado fuera de orden** extremo a extremo (POST firmado al webhook → worker → bandeja) (AC-09).
- 401, módulo deshabilitado, aislamiento entre empresas en todos los endpoints (AC-10).
- Migración 0002 sobre filas existentes (AC-12).

## E2E
**NO.** No hay Playwright en el proyecto y las tareas CRM previas se verificaron con Karma por decisión del usuario; instalarlo es una dependencia nueva que requiere confirmación. El flujo «recibir → asignar → vincular» queda cubierto por pruebas de integración de API con proveedor simulado y pruebas de componentes Karma. Si el usuario quiere Playwright, se añade en una tarea propia.

## Regression tests
Suites existentes de `messaging` y `crm` deben seguir verdes (webhook, worker, envío, oportunidades, prospectos).

## Frontend (Karma)
Servicio `crm-inbox-api.service` (rutas y parámetros), página `crm-inbox` (lista, filtros, abrir conversación, responder con ventana abierta/cerrada, reenviar, asignar, vincular, estados vacío/error, limpieza del temporizador), diálogos, y clave i18n completa en es/en/pt (`npm run i18n:check`).

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | Integración (listado/filtros/paginado) + Karma lista |
| AC-02 | Integración (hilo, `after`) + Karma servicio |
| AC-03 | Integración (ventana/plantilla) + Karma caja de respuesta |
| AC-04 | Integración (fallo y reintento) + Karma botón Reenviar |
| AC-05 | Integración + Karma diálogo asignar |
| AC-06 | Integración + Karma diálogo contacto |
| AC-07 | Integración (vincular/crear/incompatible) + Karma diálogo oportunidad |
| AC-08 | Unit `InboxService` + integración con evento real |
| AC-09 | Integración extremo a extremo vía webhook y worker |
| AC-10 | Integración (401/403/otra empresa) |
| AC-11 | Karma (página, menú, responsive por clases) + `i18n:check` + revisión visual de `delivery-publish` |
| AC-12 | Prueba de migración con datos previos |

# Implementation Plan

## Architecture considerations
Ver ADR. `messaging` no importa `crm`; `crm` solo entra por `modules.messaging.services`. El dominio de ambos sin Django.

## Proposed solution
1. `messaging`: columnas opacas y métodos del agregado; fachada `services.py`; `Message.requeue()`.
2. `crm`: puerto `ConversationInbox`, `InboxService`, adaptador, vistas/URLs `/api/crm/inbox/`, suscriptor de `InboundMessageReceived`.
3. Frontend: modelo, servicio, página y diálogos, ruta y menú, plantilla en el sistema de diseño, i18n.

## Files/components affected
- **Backend `messaging`**: `domain/entities.py` (`Conversation`, `Message.requeue`), `infrastructure/django/models.py` y `repositories.py`, nueva `migrations/0002_conversation_inbox_links.py`, nueva `services.py` (fachada), tests.
- **Backend `crm`**: `application/ports.py`, nuevo `application/inbox_services.py`, `infrastructure/adapters.py`, `infrastructure/django/repositories.py` (búsqueda de prospecto por teléfono normalizado), nuevos `api/inbox_views.py`, `inbox_serializers.py`, `inbox_urls.py`, `config/urls.py` (ruta), `apps.py` (suscripción), tests.
- **Frontend**: `features/crm/models/inbox.ts`, `services/crm-inbox-api.service.ts`(+spec), `pages/crm-inbox/*`, `components/inbox-*-dialog/*`, `crm.routes.ts`, ruta principal y `assets/data/routes.json` (menú), `assets/i18n/{es,en,pt}.json`.
- **Docs**: `docs/design/design-system.md` (§5, plantilla «Bandeja de conversaciones»).

## Implementation steps
1. Migración `0002` + dominio `Conversation`/`Message.requeue` + repositorios (INV-02, 03, 08, 09; AC-12).
2. Fachada `messaging/services.py`: listar/leer, enviar texto/plantilla, reencolar, asignar y vincular (INV-10; AC-03, 04).
3. `crm`: puerto, `InboxService` (reglas INV-03…07), adaptador y búsqueda de prospecto por teléfono (AC-05…08).
4. API `/api/crm/inbox/` con permisos, módulo y errores 400/404/409 (API-01…08; AC-01, 02, 10).
5. Suscriptor de `InboundMessageReceived` y su alta en `CrmConfig.ready()` (AC-08).
6. Pruebas backend de integración incluyendo webhook→worker→bandeja (AC-09) y dos empresas.
7. Frontend: servicio y modelos (API-01…08).
8. Frontend: página Bandeja y diálogos, ruta, menú, i18n es/en/pt (UI-01…07; AC-11).
9. Plantilla en `design-system.md`; ruff/flake8 en lo cambiado; `npm test`, `npm run lint`, `npm run i18n:check`, `npm run build`.

## Database / migrations
Nueva `messaging/0002_conversation_inbox_links.py` (aditiva, nullable, 2 índices). No se edita ninguna migración aplicada. Rollback: `migrate messaging 0001`.

## Risks
Acoplamiento crm↔messaging (fachada + puerto); autovínculo erróneo (solo coincidencia única); suscriptor registrado también en el worker (probar con el comando real o su caso de uso); consulta periódica con muchas pestañas (intervalo 10 s, solo visible); validación contra Meta real pendiente.

## New dependencies
Ninguna. (Playwright se descarta aquí; requeriría confirmación previa.)
