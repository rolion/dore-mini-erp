# ADR-crm-integracion-whatsapp-cloud-api-modulo-messaging-y-cola-de-eventos: Módulo `messaging` con puerto MessagingGateway, secretos por referencia y cola en base

**Estado:** Propuesto
**Task relacionado:** TASK-crm-integracion-whatsapp-cloud-api
**Fecha:** 2026-11-27

## Contexto
PB-CRM-016 conecta el número de WhatsApp de cada empresa a la Cloud API de Meta (sin BSP): recibe mensajes y estados por webhook y envía texto, interactivos y plantillas. Habilita bandeja (PB-CRM-012), campañas (013), asistente (018) y citas (020/021). Hoy no existe nada de mensajería, ni Celery/Redis, ni gestor de secretos; la importación en segundo plano resolvió el mismo problema de «responder rápido y procesar aparte» con cola en BD + worker (`ADR-importacion-en-segundo-plano-cola-en-base-de-datos-y-worker`).

## Decisión
1. **Módulo nuevo `backend/modules/messaging/`** (no dentro de `crm`): mensajería es infraestructura de comunicación que usarán CRM, agenda y campañas. Contiene `Conversation`, `Message`, `WhatsAppConnection`, `MessageTemplate`. `crm`/`agenda` lo consumirán por fachada o por el evento `InboundMessageReceived`; `messaging` no importa otros módulos de negocio. El teléfono se normaliza con la regla ya existente de `DEFAULT_PHONE_COUNTRY_CODE`.
2. **Puerto `MessagingGateway`** en `domain/`/`application/ports.py` (`send_text`, `send_interactive`, `send_template`, `sync_templates`) con dos adaptadores en `infrastructure/`: `WhatsAppCloudAdapter` (HTTP a `graph.facebook.com`, versión de API fija en settings) y `FakeMessagingGateway` (proveedor simulado para desarrollo y pruebas, sin red).
3. **Webhook público** `GET/POST /api/messaging/whatsapp/webhook/` (sin autenticación de usuario, exento de CSRF/token DRF). `GET`: devuelve `hub.challenge` solo si `hub.verify_token` coincide con el de una conexión (403 si no). `POST`: valida `X-Hub-Signature-256` (HMAC-SHA256 del cuerpo crudo con el App Secret de la conexión resuelta por `phone_number_id`) con `hmac.compare_digest`; firma inválida → 401 sin persistir; válida → **inserta el cuerpo en `WebhookEvent` y responde 200** sin más trabajo. La empresa sale de la conexión guardada, nunca del payload.
4. **Cola en base, sin dependencias nuevas** (decisión del usuario, 2026-11-27, en lugar de Celery de la tarjeta): `WebhookEvent` (`pending/processing/done/failed`, intentos) y los `Message` salientes (`queued` con `next_attempt_at`) los procesa `python manage.py run_messaging_worker` (sondeo ~2 s, `--once`, `select_for_update(skip_locked=True)`), nuevo servicio `messaging-worker` en `compose.yaml` con la misma imagen. `process_webhook_event` es el caso de uso que ejecuta el worker. Si más adelante se adopta Celery, el caso de uso no cambia.
5. **Idempotencia**: `UNIQUE(connection_id, provider_message_id)` en `Message`; un `wamid` repetido no crea otro mensaje.
6. **Estados sin retroceso**: orden `queued < sent < delivered < read`; un estado de menor rango no sobrescribe. `failed` solo aplica si el mensaje aún no está `delivered`/`read`. Transiciones por métodos del agregado `Message`.
7. **Ventana de 24 h**: `Conversation.last_inbound_at`; `WindowPolicy` (dominio, función pura, límite exacto: abierta si `now - last_inbound_at <= 24 h`). Texto/interactivo fuera de ventana → `WindowClosed`; plantilla exige estado `APPROVED`.
8. **Reintentos**: 429/5xx/timeouts → backoff exponencial con tope (p. ej. 1, 2, 4, 8, 16 min; 5 intentos) reprogramando `next_attempt_at`; agotados → `failed` con `failure_reason`. 4xx de cliente (token expirado = error 190, número inválido) → `failed` sin reintentar; token expirado marca la conexión `error` para que la pantalla lo muestre.
9. **Secretos**: la BD guarda solo `secret_ref` y `app_secret_ref`, que son **nombres de variables de entorno** del servidor (siempre con el prefijo propio de la empresa, `WHATSAPP_<12 hex del company_id>_…`, para que una empresa no pueda apuntar al secreto de otra: REV-01); un `SecretResolver` (puerto) los lee en el momento de usar. Nunca se loguean ni se serializan (los serializers no exponen los refs completos de vuelta ni valores). `verify_token` es un valor aleatorio no secreto, generado por PocketBiz.
10. **Costos**: del webhook se guardan `pricing_category`, `billable` y `pricing_model`; `cost` (`Decimal`) y `currency` quedan nulos hasta una conciliación posterior con la analítica de Meta (decisión del usuario, 2026-11-27).

## Alternativas consideradas
- **Celery + Redis** (tarjeta): estándar, pero añade dos dependencias y un servicio; el volumen inicial no lo exige y ya hay un patrón de worker propio. Diferida.
- **Dentro de `crm`**: acopla agenda y campañas a CRM. Descartada.
- **Token cifrado en BD** (campo `EncryptedField`): requiere gestionar una clave maestra y una dependencia; la referencia a entorno cumple «nunca en texto plano» con menos piezas. Cambiar a un gestor externo solo toca `SecretResolver`.
- **Procesar el webhook en la petición**: viola el requisito de responder < 2 s y reintenta mal.

## Estrategia de rollback / mitigación
- Migraciones nuevas solo crean tablas del módulo (reversibles; no tocan tablas existentes).
- La integración es opt-in por empresa: sin `WhatsAppConnection` no ocurre nada. Se desactiva con `status=disabled` o quitando el webhook en Meta.
- Si el worker no corre, los eventos quedan `pending` y los envíos `queued`; no se pierden (Meta además reintenta el webhook durante días si no recibe 200). `run_messaging_worker --once` los procesa a mano.
- Revertir = revertir el commit y `docker compose up -d --remove-orphans`.

## Consecuencias
- Un servicio más en producción (`messaging-worker`) y un comando que operar.
- Secretos fuera de la BD: alta de una empresa requiere que quien despliega añada variables de entorno (se documenta; limita el autoservicio hasta que haya gestor de secretos).
- El webhook es el primer endpoint público sin sesión: queda cubierto por firma HMAC, límite de tamaño de cuerpo y pruebas de seguridad.
- `cost` nulo hasta la conciliación: los informes de costo de campañas (PB-CRM-013) deberán esperar o usar categoría.
