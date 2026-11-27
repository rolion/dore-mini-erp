# TASK-crm-integracion-whatsapp-cloud-api: PB-CRM-016 · Integración WhatsApp Cloud API

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** `task/TASK-crm-integracion-whatsapp-cloud-api` (base: `crm`)
**Pull Request:** _sin abrir todavía_
**Fuente:** https://trello.com/c/P0ScFUjk/16-pb-crm-016-integraci%C3%B3n-whatsapp-cloud-api

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-27 | (nuevo) → INVESTIGATION | Task creado desde tarjeta de Trello | delivery-start |
| 2026-11-27 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | Decisiones de negocio/técnicas respondidas por el usuario; DDR y ADR escritos | delivery-start |
| 2026-11-27 | PLANNING → ENGINEERING | Plan v1 COMPLETO, Specification READY | delivery-start |

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
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
