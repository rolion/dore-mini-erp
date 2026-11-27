# TASK-crm-integracion-whatsapp-cloud-api: PB-CRM-016 · Integración WhatsApp Cloud API

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** `task/TASK-crm-integracion-whatsapp-cloud-api` (base: `crm`)
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/141
**Fuente:** https://trello.com/c/P0ScFUjk/16-pb-crm-016-integraci%C3%B3n-whatsapp-cloud-api

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-27 | (nuevo) → INVESTIGATION | Task creado desde tarjeta de Trello | delivery-start |
| 2026-11-27 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | Decisiones de negocio/técnicas respondidas por el usuario; DDR y ADR escritos | delivery-start |
| 2026-11-27 | PLANNING → ENGINEERING | Plan v1 COMPLETO, Specification READY | delivery-start |
| 2026-11-27 | ENGINEERING → REVIEW | Implementación completa según PLAN v1 | delivery-build |
| 2026-11-27 | REVIEW → PUBLISH | Quality Gate PASS con reservas (sin Critical/High; REV-01 Medium y REV-02..04 Low abiertos) | delivery-publish |
| 2026-11-27 | PUBLISH | REV-01..04 corregidos a pedido del usuario; backend 2622 y frontend 1976 pruebas OK | delivery-build |
| 2026-11-27 | PUBLISH | Segundo Quality Gate PASS con reservas: REV-01..04 verificados como resueltos; REV-05..08 (Low) abiertos | delivery-publish |

## Investigación

### Requerimiento
Insumo (tarjeta Trello PB-CRM-016, no Specification aprobada): *Como administrador, quiero conectar el número de WhatsApp de mi empresa a PocketBiz para enviar y recibir mensajes desde el CRM.* Integración directa con la Cloud API de Meta (sin BSP); puerto `MessagingGateway` y adaptador `WhatsAppCloudAdapter`; webhook de mensajes y estados; envío de texto, interactivos (lista/botones) y plantillas; ventana de 24 h; registro del costo informado por Meta. 9 criterios de aceptación (verificación GET, firma 401, < 2 s con cola, idempotencia por wamid, `WindowClosed`, estados sin retroceso, backoff, pricing/costo, secretos por `secret_ref`). UI: Configuración → Integraciones → WhatsApp (WABA ID, phone_number_id, estado, mensaje de prueba, plantillas). Modelos: `WhatsAppConnection`, `MessageTemplate`, `Conversation.last_inbound_at`, `Message`; evento `InboundMessageReceived`. Tests: unidad, integración con payloads reales y Playwright. Sin dependencias de otras tarjetas; habilita PB-CRM-012, -013, -018, -020, -021. Puede avanzar con proveedor simulado mientras Meta verifica el negocio.

Aclaraciones del usuario: «usa la rama de crm» (base y destino del PR) y «analiza qué configuración tengo que hacer en el lado de WhatsApp» → guía en `docs/integrations/whatsapp-cloud-api-configuracion-meta.md`. Decisiones (2026-11-27): (1) webhooks por **cola en BD + worker** en lugar de Celery; (2) del costo se guarda la **categoría** y `cost`/`currency` quedan nulos hasta conciliar con la analítica de Meta.

### Hechos encontrados
- `backend/modules/` no tiene `messaging` ni nada de WhatsApp; `crm` solo tiene tablero, prospectos, oportunidades, tareas y actividad (`backend/modules/crm/infrastructure/django/models.py:8-154`). La actividad ya prevé el canal `whatsapp` (`backend/modules/crm/domain/activity.py`).
- No hay Celery ni Redis: `backend/requirements/base.txt` (Django, DRF, psycopg, django-environ, openpyxl).
- Patrón de trabajo en segundo plano: cola en BD + `python manage.py run_import_worker` (`docs/adr/ADR-importacion-en-segundo-plano-cola-en-base-de-datos-y-worker.md`; servicio `import-worker` documentado en `docs/deployment/docker.md:55-61`).
- Secretos: la configuración usa `django-environ` y `.env` (`backend/config/settings/base.py:3-9`); no existe gestor de secretos ni campos cifrados.
- Normalización de teléfono con `DEFAULT_PHONE_COUNTRY_CODE` (`backend/config/settings/base.py:85`).
- Aislamiento por empresa: `shared/tenancy.py`; los módulos hablan por puertos/adaptadores (`backend/modules/crm/application/ports.py`, `infrastructure/adapters.py`).
- Frontend: sin menú «Integraciones»; Configuración solo tiene `settings/modules` (`frontend/panel_admin/src/assets/data/routes.json:485-497`); plantillas de pantalla de configuración en `docs/design/design-system.md:139,144`.
- No hay Playwright (las tareas CRM previas verificaron con Karma por decisión del usuario).
- Ningún endpoint público sin sesión existe todavía (salvo `health` y auth).

### Hipótesis / supuestos no confirmados
- `secret_ref` = nombre de variable de entorno (decisión de diseño, ADR).
- Una conexión de WhatsApp por empresa en esta tarea (el modelo no lo impide).
- Meta entrega `pricing` en el estado `sent`/`delivered` según versión; el parser debe ser tolerante.
- El nombre del módulo en `modularity` y el control de rol administrador se confirman al construir.

### Módulos y dependencias relacionadas
Nuevo `messaging`; `crm`/`agenda` lo usarán después; `modularity` (alta del módulo), `shared.tenancy`.

### Implementaciones similares existentes
Worker de importación (`data_import`), puertos/adaptadores de `crm`, pantallas de configuración de `settings` e `inventory`.

### Comportamiento actual
No se puede recibir ni enviar mensajes desde el sistema.

### Restricciones
`CLAUDE.md`: `company_id` en todo, dominio sin Django, `Decimal` para dinero, no editar migraciones aplicadas, no leer `.env`, avisar antes de instalar dependencias, i18n es/en/pt sin texto hardcodeado, Reactive Forms.

### Riesgos identificados
Payloads reales de Meta, verificación del negocio pendiente, endpoint público, secretos fuera de BD que exigen operación en el despliegue, esquema compartido con PB-CRM-012.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — integración externa, módulo nuevo, endpoint público y manejo de secretos.

### Diseño requerido
**SI** — pantalla nueva de configuración con estados y formularios.

## Diseño
`docs/design/DDR-crm-integracion-whatsapp-cloud-api-pantalla-de-integracion-whatsapp.md`.

## Arquitectura
`docs/adr/ADR-crm-integracion-whatsapp-cloud-api-modulo-messaging-y-cola-de-eventos.md`.

## Plan
`docs/plans/PLAN-2026-11-27-crm-integracion-whatsapp-cloud-api.md` (v1, COMPLETO). Specification readiness: READY.

## Implementación

**Backend** (`backend/modules/messaging/`, módulo nuevo `domain/ application/ infrastructure/ api/`):
- `domain/rules.py` — ventana de 24 h (límite inclusivo), normalización de teléfono, firma HMAC en tiempo constante, backoff, validación de `secret_ref` (INV-04, 05, 06; AC-05, AC-09). `domain/entities.py` — `Message.advance/mark_sent/fail/schedule_retry` (estados sin retroceso, INV-03; AC-06, AC-07), `Conversation`, `Connection`, `Template`. `domain/webhook.py` — parser tolerante (mensajes, estados, `pricing`).
- `application/services.py` — `ReceiveWebhook` (valida e inserta; AC-01..03), `ProcessWebhookEvent` (idempotencia por wamid, `last_inbound_at`, evento `InboundMessageReceived`; AC-04, 08, 10), `SendMessages` (texto/interactivo/plantilla, entrega con reintentos, sincronización de plantillas), `ConnectionService`.
- `infrastructure/` — modelos y migración `0001_initial` (INV-01/02/07/08), repositorios por `company_id` y colas (`EventQueue`, `OutboxQueue` con arrendamiento), `WhatsAppCloudAdapter` (urllib, sin dependencias nuevas), `FakeMessagingGateway`, `EnvSecretResolver`, worker y comando `run_messaging_worker`.
- `api/` — webhook público (GET verificación, POST firmado), conexión, mensaje de prueba, plantillas (API-01..05). Settings: `MESSAGING_PROVIDER`, `WHATSAPP_API_BASE_URL`, `WHATSAPP_API_VERSION`. `compose.yaml`: servicio `messaging-worker`. `.env.example` y `docs/deployment/docker.md` actualizados.

**Frontend** (`features/settings/`): `models/whatsapp.ts`, `services/whatsapp-api.service.ts`, `pages/whatsapp-integration` (plantilla «Formulario de configuración» + listado; DDR), ruta `settings/integrations/whatsapp`, entrada de menú y claves i18n es/en/pt (AC-11, UI-01..03). Referencia visual: `module-settings`/`module-list`; sin componentes compartidos nuevos.

**Pruebas:** `messaging/tests/test_domain.py` (17) y `test_api.py` (33) cubren AC-01..AC-11 (ver mapeo del PLAN); Karma: servicio y página (13). Se ajustó `sidebar-menu.spec.ts` (cuenta de entradas y submenú de Configuración).

**Desviaciones respecto al plan**
- `required_modules = ()`: `messaging` no se registró en el registro de `modularity` (cambiaría los conteos de módulos por tipo de empresa y las configuraciones por defecto); el acceso es solo para el administrador de la empresa. Registrarlo queda para cuando se defina cómo se habilita por tipo de empresa.
- La API devuelve los **nombres** `secret_ref`/`app_secret_ref` (no son secretos y la pantalla los edita); nunca valores.
- `secret_ref` solo admite nombres `WHATSAPP_*` (no estaba en el plan): evita que un administrador de empresa apunte a `SECRET_KEY` o `DATABASE_URL` y los envíe a Meta.
- Estado de conexión: `active` si ambas variables existen al guardar o tras sincronizar plantillas; `pending/secrets_missing` si faltan; `error/token_expired` ante el código 190 de Meta.
- Envío de interactivos implementado en servicio y adaptador sin endpoint público (la bandeja PB-CRM-012 lo usará).
- E2E Playwright no aplica (decidido en el PLAN); la prueba real con Meta queda como verificación manual.

**Correcciones tras el Quality Gate (REV-01..04):** variables de secreto con prefijo propio de la empresa (`WHATSAPP_<12 hex del company_id>_`; la API devuelve `secret_ref_prefix`); eventos firmados de conexiones `disabled` responden 200 sin efecto; procesamiento de cada evento en una transacción y publicación del evento de dominio solo tras confirmar; pantalla con pestañas, `ng-select`, `aria-label` en «Copiar», menú `adminOnly`.

**Deuda técnica / límites conocidos**
- Un estado que llegue antes de que se guarde el wamid del envío se ignora (worker secuencial: poco probable; con varias réplicas podría perderse un estado).
- `cost`/`currency` siempre nulos hasta la conciliación con la analítica de Meta (decisión del usuario).
- Sin gestor de secretos: alta de empresas exige variables de entorno en el despliegue.
- La suite del backend en `--parallel` aborta sin traza por falta de `tblib` (preexistente); se corrió en serie.


## Review
**Quality Gate: PASS con reservas** (subagente aislado, 2026-11-27). Backend completo 2617 pruebas OK; frontend 1973 OK; lint y `i18n:check` limpios; `npm run build` OK; bandit sin Medium/High en código de producción. Estado visual en navegador: **no verificado** (no se levantó la app).

| REV | Severidad | Categoría | Tema |
|---|---|---|---|
| REV-01 | Medium | IMPLEMENTATION | Una empresa puede apuntar su `secret_ref` a la variable `WHATSAPP_*` de otra (sin propiedad/unicidad de la referencia; además el estado revela si existe) |
| REV-02 | Low | IMPLEMENTATION | Evento firmado de una conexión `disabled` responde 401 en vez de ignorarse (latente) |
| REV-03 | Low | IMPLEMENTATION | `ProcessWebhookEvent._inbound` no es atómico: un fallo tras insertar deja la ventana sin abrir y el evento sin publicar |
| REV-04 | Low | DESIGN | Desviaciones no declaradas del DDR (sin pestañas, `<select>` nativo, «Copiar» sin `aria-label`, menú sin `adminOnly`, ruta de archivo en el texto de ayuda) |

**Actualización:** REV-01..04 corregidos a pedido del usuario y marcados `Closed` (ver «Resolución» en cada uno). Tras la corrección: backend completo 2622 pruebas OK, frontend 1976 OK, lint e `i18n:check` limpios. 

**Segundo Quality Gate (aislado, tras las correcciones): PASS con reservas.** REV-01..04 verificados como resueltos. Backend 2622 y frontend 1976 pruebas OK; lint, `i18n:check` y `build` limpios; bandit sin Medium/High. Hallazgos nuevos, todos Low y abiertos: REV-05 (publicación del evento de dominio en memoria, no durable; la prueba «tras commit» no lo distingue), REV-06 (PLAN/DDR/TASK/ADR no reflejan el prefijo por empresa ni `secret_ref_prefix`), REV-07 (el resolvedor de secretos no exige el prefijo al usar, solo al guardar), REV-08 (pestañas sin navegación por flechas y `copy()` sin manejo de error ni `aria-live`). Estado visual en navegador: **no verificado**.

## Publicación
PR listo para aprobación humana (no se mergea). Cambio sensible: **autenticación/seguridad** (endpoint público firmado, manejo de secretos), **base de datos** (migración inicial de `messaging`) e **infraestructura** (servicio `messaging-worker`); respaldado por el ADR `ADR-crm-integracion-whatsapp-cloud-api-modulo-messaging-y-cola-de-eventos`. Pendiente humano: prueba real con el número de prueba de Meta, variables `WHATSAPP_*` en el despliegue y decisión sobre REV-01.
