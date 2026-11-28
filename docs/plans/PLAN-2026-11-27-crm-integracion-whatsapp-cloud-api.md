# PLAN-2026-11-27-crm-integracion-whatsapp-cloud-api (v2)

**Task:** TASK-crm-integracion-whatsapp-cloud-api · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-crm-integracion-whatsapp-cloud-api-pantalla-de-integracion-whatsapp / ADR-crm-integracion-whatsapp-cloud-api-modulo-messaging-y-cola-de-eventos

## Changelog
- **v2 (2026-11-27)** — `[Specification]` aclaración pedida por el usuario al corregir REV-06 (no cambia AC): INV-05 y API-03 recogen la regla del prefijo de secretos por empresa (REV-01) y su validación también al usar la referencia (REV-07). `[Implementation Plan]` sin cambios.
- v1 — versión inicial.

## Objective
Que el administrador conecte el número de WhatsApp de su empresa (Cloud API directa) y que el sistema reciba mensajes y estados de forma segura e idempotente, y envíe texto, interactivos y plantillas respetando la ventana de 24 h.

## Context
Resumen en `docs/tasks/TASK-crm-integracion-whatsapp-cloud-api.md`; configuración requerida en Meta en `docs/integrations/whatsapp-cloud-api-configuracion-meta.md`. Base y destino del PR: rama `crm`.

# Specification

## Domain context
Bounded context nuevo `messaging` (ADR). `crm` y `agenda` lo consumirán después (PB-CRM-012/013/018/020/021); en esta tarea nadie lo consume salvo su propia pantalla. `messaging` no importa módulos de negocio.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Conexión (`WhatsAppConnection`) | Número de WhatsApp de una empresa en una WABA | Tarjeta |
| Conversación | Hilo con un teléfono de una conexión; guarda `last_inbound_at` | Tarjeta |
| Mensaje | Entrante o saliente con `provider_message_id` (wamid) | Tarjeta |
| Ventana de servicio | 24 h desde el último mensaje entrante; solo en ella se envía texto libre | Tarjeta |
| Plantilla | Mensaje preaprobado por Meta, único permitido fuera de ventana | Tarjeta |
| `secret_ref` | Nombre de la variable de entorno que contiene el secreto | ADR (decisión de diseño) |

## Current behavior
No existe mensajería, ni worker de mensajes, ni endpoints públicos sin sesión. Ver `docs/tasks/TASK-crm-integracion-whatsapp-cloud-api.md` (Hechos).

## Expected behavior
Webhook verificable, firmado y rápido; eventos persistidos y procesados por un worker; mensajes únicos por wamid; estados que solo avanzan; envíos con control de ventana, reintentos y registro de la categoría de precio.

## Domain rules / invariants
- **INV-01** Toda fila (`WhatsAppConnection`, `MessageTemplate`, `Conversation`, `Message`, `WebhookEvent`) lleva `company_id`; en el webhook la empresa sale de la conexión resuelta por `phone_number_id`, nunca del payload.
- **INV-02** `UNIQUE(connection_id, provider_message_id)`; dos conexiones activas no comparten `phone_number_id` (único global) ni `verify_token`.
- **INV-03** Orden de estados `queued < sent < delivered < read`; un estado de menor o igual rango no modifica el mensaje. `failed` no pisa `delivered`/`read`. Cambios por métodos del agregado (`message.mark_sent()`, …), nunca por asignación.
- **INV-04** Ventana abierta ⇔ `last_inbound_at` existe y `now - last_inbound_at <= 24 h` (límite exacto inclusivo). Texto/interactivo con ventana cerrada → `WindowClosed`. Plantilla solo si `status = APPROVED`, si no → `TemplateNotApproved`.
- **INV-05** Los secretos nunca se persisten ni se loguean; solo `secret_ref`/`app_secret_ref` (nombres de variable). Las respuestas de la API no devuelven valores secretos. Cada empresa solo puede nombrar variables con su propio prefijo `WHATSAPP_<12 hex del company_id en mayúsculas>_` (y más caracteres tras él): se valida al guardar y otra vez al resolver el secreto, para que una empresa no use la variable de otra ni `SECRET_KEY`/`DATABASE_URL`.
- **INV-06** Teléfonos normalizados (solo dígitos, código de país; `DEFAULT_PHONE_COUNTRY_CODE` para números locales) antes de buscar/crear conversación.
- **INV-07** `cost` y `currency` son `Decimal`/texto nulos por ahora; `pricing_category`, `billable`, `pricing_model` se guardan cuando Meta los informa.
- **INV-08** Conexión con `status` ∈ {`pending`, `active`, `error`, `disabled`}; un token expirado la pasa a `error` con motivo.

## Acceptance criteria
(Los 9 de la tarjeta, sin cambios de alcance.)
- **AC-01** GET del webhook devuelve `hub.challenge` solo con el `verify_token` correcto; con otro responde 403.
- **AC-02** POST con firma `X-Hub-Signature-256` inválida o ausente → 401 y no persiste nada.
- **AC-03** El webhook responde en < 2 s; el procesamiento ocurre en el worker (cola en BD, ADR; la tarjeta decía Celery y el usuario eligió cola en BD).
- **AC-04** El mismo wamid recibido dos veces genera un solo `Message`.
- **AC-05** Enviar texto libre fuera de ventana falla con `WindowClosed`.
- **AC-06** Un estado fuera de orden (read antes de delivered) no retrocede el estado.
- **AC-07** Ante 429/5xx de Meta se reintenta con backoff exponencial; agotados los intentos el mensaje queda `failed` con el motivo.
- **AC-08** Se guardan `pricing_category` (y `billable`, `pricing_model`); `cost`/`currency` quedan nulos hasta conciliación (**ajuste respecto a la tarjeta, aprobado por el usuario 2026-11-27**).
- **AC-09** Tokens y App Secret solo como `secret_ref`; nunca en texto plano en BD ni en logs.
- **AC-10** El mensaje entrante persistido publica el evento de dominio `InboundMessageReceived` (una vez).
- **AC-11** Interfaz: guardar la conexión, enviar mensaje de prueba y ver plantillas sincronizadas con su estado (DDR).

## Edge cases / Error cases
Payload de Meta con estructura desconocida → se marca `done` sin efecto, no `failed`; evento de una conexión `disabled` → ignorado; tipo de mensaje no soportado (imagen, audio…) → se guarda `type` con `content` mínimo; conexión borrada con eventos pendientes → `failed` con motivo; token expirado (error 190) → `failed` sin reintento y conexión a `error`; doble envío de prueba → dos mensajes distintos (sin idempotencia de salida en esta tarea); payload > 1 MB → 413.

## Authorization / permissions
Webhook: público, protegido por firma HMAC. Resto de la API: usuario autenticado con rol administrador de la empresa y módulo habilitado; 403 en otro caso; `company_id` del usuario (`shared/tenancy.py`).

## API contract
- **API-01** `GET /api/messaging/whatsapp/webhook/` → 200 `hub.challenge` (texto) | 403.
- **API-02** `POST /api/messaging/whatsapp/webhook/` → 200 `{}` | 401 | 413 (nunca 4xx por contenido válido-firmado).
- **API-03** `GET/PUT /api/messaging/whatsapp/connection/` (una conexión por empresa): `waba_id, phone_number_id, display_phone, secret_ref, app_secret_ref, verify_token (solo lectura), status, status_reason, webhook_url, secret_ref_prefix` (solo lectura; prefijo obligatorio de ambos nombres, también sin conexión creada).
- **API-04** `POST /api/messaging/whatsapp/test-message/` `{to, template_id}` → 202 `{message_id, status}`; errores de dominio → 409/400 con código (`window_closed`, `template_not_approved`, `connection_not_active`).
- **API-05** `GET /api/messaging/whatsapp/templates/` y `POST …/templates/sync/`.
Todo es nuevo; sin impacto en contratos existentes.

## UI behavior
- **UI-01** Menú Configuración → Integraciones → WhatsApp; plantilla «Formulario de configuración» + «Listados en pestañas» (design-system §5) según DDR.
- **UI-02** Estados cargando/vacío/error/éxito, badges de plantilla (aprobada/rechazada/pausada/pendiente), confirmación al cambiar WABA/phone_number_id, copiar URL del webhook y verify token.
- **UI-03** Textos en es/en/pt; accesos con `aria-label`.

## Non-functional requirements
Respuesta del webhook < 2 s (solo valida firma e inserta); comparación de firma en tiempo constante; versión de la Graph API fija en settings; timeout de HTTP saliente 10 s; logs sin cuerpos de mensajes ni tokens.

## Out of scope
Bandeja y asignación (PB-CRM-012), campañas (013), asistente (018), citas (020/021); medios (imágenes/audio/documentos) salientes; creación de plantillas desde PocketBiz; conciliación del costo monetario; gestor de secretos externo; Celery/Redis; Playwright.

## Open questions
- Cuándo y cómo conciliar `cost` con la analítica de Meta (no bloquea).
- Si los mensajes de la app móvil en coexistencia deben guardarse (no bloquea; se ignoran).

# Test Specification

## Unit tests
`WindowPolicy` (límite exacto 24 h, sin entrante, futuro), orden de estados, normalización de teléfono, cálculo de backoff, validación de firma (HMAC, cuerpo alterado), parseo de payloads de Meta (mensaje, estado, desconocido), `SecretResolver` (variable ausente → error sin filtrar el nombre del valor).

## Integration tests (API + worker, `FakeMessagingGateway` y cliente HTTP simulado)
Verificación GET (AC-01), firma inválida (AC-02), tiempo y no procesamiento en la petición (AC-03), wamid repetido (AC-04), `WindowClosed` (AC-05), estados fuera de orden (AC-06), 429/5xx con reintento y agotamiento (AC-07), pricing guardado (AC-08), logs sin secretos y respuestas sin secretos (AC-09), evento publicado una vez (AC-10), aislamiento por `company_id`, 403 a no administrador, conexión `error` por token expirado. Fixtures: payloads reales de Meta del número de prueba (se capturan en la verificación manual; hasta entonces, payloads de la documentación oficial).

## E2E
**NO** — Playwright no está instalado y exige dependencia nueva; las tareas CRM anteriores verificaron la interfaz con Karma por decisión del usuario. La interfaz se cubre con pruebas de componente/servicio (Karma) y la integración real con Meta, con una verificación manual guiada con el número de prueba.

## Regression tests
Suite completa del backend y `npm test`/`i18n:check`/`lint` del frontend.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01, AC-02 | Integración API webhook |
| AC-03 | Integración (el handler solo inserta; test de que no llama al gateway ni al caso de uso) |
| AC-04, AC-10 | Integración worker + unidad del agregado |
| AC-05 | Unidad `WindowPolicy` + integración envío |
| AC-06 | Unidad estados + integración worker |
| AC-07 | Integración con cliente HTTP simulado (429/5xx/agotado) |
| AC-08 | Integración worker de estados |
| AC-09 | Integración (serializer sin secretos, caplog sin tokens) + revisión del esquema de BD |
| AC-11 | Karma (servicio, página, i18n) + verificación manual |

# Implementation Plan

## Architecture considerations
Ver ADR. Capas `domain/ application/ infrastructure/ api/`; el dominio sin Django; el worker es un comando en `management/commands/`.

## Proposed solution
Módulo `messaging` con agregados `Message`/`Conversation`, `WindowPolicy`, puerto `MessagingGateway` (+ `WhatsAppCloudAdapter` y `FakeMessagingGateway`), casos de uso `ReceiveWebhook` (valida e inserta), `ProcessWebhookEvent`, `SendMessage`, `SyncTemplates`, worker `run_messaging_worker`, vistas finas y pantalla Angular.

## Files/components affected
- Backend: `backend/modules/messaging/**` (nuevo), registro en `config/settings/base.py` y `config/urls.py`, módulo en `modularity` (por verificar al construir), `compose.yaml` (servicio `messaging-worker`), `.env.example` (nombres de variables), `docs/deployment/docker.md`.
- Frontend: `features/settings/pages/whatsapp-integration` (o `features/messaging/`), servicio API, rutas, `routes.json`, i18n es/en/pt.
- Docs: guía de Meta (ya incluida).

## Implementation steps
1. Dominio: errores (`WindowClosed`, `TemplateNotApproved`…), `WindowPolicy`, estados de `Message`, normalización de teléfono (INV-03/04/06).
2. Modelos y migración inicial (INV-01/02/05/07/08), repositorios por `company_id`.
3. Seguridad: verificación de firma, `SecretResolver`, filtro de logs (AC-02, AC-09).
4. Webhook GET/POST que solo inserta `WebhookEvent` (AC-01..03).
5. `ProcessWebhookEvent`: mensajes entrantes (idempotencia, `last_inbound_at`, evento) y estados (AC-04, 06, 08, 10).
6. Puerto `MessagingGateway`, `WhatsAppCloudAdapter`, `FakeMessagingGateway`; `SendMessage` con ventana/plantilla y reintentos (AC-05, 07).
7. Worker + servicio compose + docs de despliegue.
8. API de conexión, prueba y plantillas (API-03..05) con permisos.
9. Frontend: pantalla según DDR + i18n + Karma (AC-11).
10. Pruebas completas, lint (`ruff`/`flake8` sobre archivos cambiados), `i18n:check`.

## Database / migrations
Migración inicial nueva del módulo `messaging`; ninguna migración existente se edita. `UNIQUE(connection_id, provider_message_id)`, `UNIQUE(phone_number_id)`, índices `(status, next_attempt_at)` para el worker.

## Risks
- Payloads reales de Meta distintos a la documentación → fixtures reales y parser tolerante.
- Verificación del negocio en Meta pendiente → desarrollo con proveedor simulado.
- Endpoint público: abuso/volumen → límite de tamaño y firma antes de leer.
- `Conversation`/`Message` compartidos con PB-CRM-012: el esquema debe prever asignación sin romper (campos añadidos luego por migración).
- El nombre de módulo de `modularity` y la forma de restringir a administradores deben confirmarse en build.

## New dependencies
Ninguna (HTTP saliente con la biblioteca estándar o la ya instalada; si se necesitara `requests`/`httpx`, se avisa antes de instalar).
