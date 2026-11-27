# Configuración en el lado de Meta / WhatsApp (Cloud API)

Guía para PB-CRM-016. Qué debe existir en Meta **antes** de conectar un número a PocketBiz y qué valor va a cada campo. Los nombres de menús de Meta cambian con frecuencia: verifica contra la documentación vigente de Meta for Developers (WhatsApp Business Platform). La integración es directa con la Cloud API, sin BSP.

> Mientras Meta verifica el negocio, el desarrollo avanza con el proveedor simulado (`FakeMessagingGateway`); nada de esto bloquea la implementación, solo la prueba real.

## 1. Cuentas y activos en Meta (una vez por empresa cliente)
| # | Qué | Para qué | Dato que se obtiene |
|---|---|---|---|
| 1 | **Business portfolio** (Meta Business Suite) con un administrador | Dueño de la WABA y de la app | — |
| 2 | **Verificación del negocio** (Security Center) | Sin ella el volumen y los límites de mensajes quedan muy restringidos; es el trámite lento | estado «Verificado» |
| 3 | **App de tipo Business** en developers.facebook.com, con el producto **WhatsApp** agregado | Es quien recibe el webhook y firma con el App Secret | **App ID**, **App Secret** |
| 4 | **WhatsApp Business Account (WABA)** | Contiene números y plantillas | **WABA ID** |
| 5 | **Número de teléfono** agregado a la WABA y verificado por SMS/llamada | Es el remitente. Un número que ya usa la app WhatsApp o WhatsApp Business no puede registrarse en la Cloud API sin migrarlo (o usar coexistencia si Meta lo permite) | **Phone number ID** (no es el teléfono), número visible |
| 6 | **Nombre para mostrar** aprobado y, si Meta lo pide, **PIN de verificación en dos pasos** del número | Sin aprobación el número queda con límites bajos | — |
| 7 | **Método de pago** en la WABA (Facturación de WhatsApp Business) | Los mensajes de plantilla y los de pago por mensaje se cobran a la WABA; sin método de pago el envío falla | — |
| 8 | **Usuario del sistema** (System User, rol admin) en Business Settings → Users, con la app y la WABA **asignadas** como activos (control total) | Token que no caduca con la sesión de una persona | — |
| 9 | **Token del usuario del sistema** generado con permisos `whatsapp_business_messaging` y `whatsapp_business_management`, sin expiración | Autoriza envíos y la sincronización de plantillas | **Token (secreto)** |
| 10 | App en modo **Live** (no Development) | En Development solo llegan eventos de usuarios con rol en la app | — |

## 2. Webhook (después de desplegar PocketBiz con HTTPS público)
1. En la app → WhatsApp → Configuration → Webhook: **Callback URL** = `https://<dominio>/api/crm/whatsapp/webhook/` (ruta definitiva en el PLAN) y **Verify token** = el `verify_token` generado por PocketBiz para esa conexión. Meta hace un `GET` con `hub.mode=subscribe`, `hub.verify_token` y `hub.challenge`; PocketBiz devuelve el challenge solo si el token coincide (403 si no).
2. Suscribir el campo **`messages`** (cubre mensajes entrantes **y** estados sent/delivered/read/failed). Con `message_template_status_update` se pueden recibir además aprobaciones/rechazos de plantillas (opcional; la sincronización por API lo cubre).
3. **Suscribir la app a la WABA**: `POST /{waba_id}/subscribed_apps` con el token. Sin este paso Meta no entrega eventos de esa WABA aunque el webhook esté verificado.
4. El webhook se firma con `X-Hub-Signature-256` = HMAC-SHA256 del **cuerpo crudo** con el **App Secret**; PocketBiz lo valida antes de leer nada. La URL debe ser pública con certificado válido (en local, un túnel; no funciona contra `localhost`).

## 3. Plantillas
- Se crean y envían a aprobación en WhatsApp Manager (o por API `POST /{waba_id}/message_templates`). Categorías: `UTILITY`, `MARKETING`, `AUTHENTICATION`; la categoría define el precio y Meta puede recategorizarla.
- Solo las `APPROVED` se pueden enviar. PocketBiz las sincroniza (`GET /{waba_id}/message_templates`) y muestra su estado.
- Fuera de la **ventana de servicio de 24 h** (contada desde el último mensaje **entrante** del cliente) solo se puede enviar una plantilla aprobada.

## 4. Qué se carga en PocketBiz (Configuración → Integraciones → WhatsApp)
| Campo de la pantalla | De dónde sale |
|---|---|
| WABA ID | Paso 4 |
| Phone number ID | Paso 5 |
| Verify token | Lo genera PocketBiz; se copia a Meta (sección 2) |
| Token del System User | **No se escribe en la pantalla ni en la BD.** Va al servidor como variable de entorno; la conexión guarda solo `secret_ref` (el nombre de la variable) |
| App Secret | Igual: variable de entorno; la conexión guarda `app_secret_ref` |

## 5. Precios (afecta al requisito de «costo informado por Meta»)
Desde julio de 2025 Meta cobra **por mensaje de plantilla entregado** (según categoría y país); los mensajes de servicio (respuestas dentro de la ventana) son gratuitos. El webhook de estado trae `pricing: {billable, pricing_model, category}` (y `type`), **no el importe**. El importe se obtiene de la analítica de precios de Meta o de su tarifa publicada. Decisión del usuario (2026-11-27): se guardan categoría, `billable` y `pricing_model`; `cost`/`currency` quedan nulos hasta una conciliación posterior.

## 6. Pruebas
- Meta entrega un **número de prueba** gratuito en la app (hasta 5 destinatarios verificados, plantilla `hello_world`); sirve para el primer envío y para ver payloads reales de webhook.
- Los fixtures de pruebas deben salir de payloads reales capturados de ese número.
- Eventos reales de otras apps de la misma WABA (mensajes de la app móvil en coexistencia) pueden llegar con campos distintos; el parser debe ignorar lo que no conoce sin fallar.
