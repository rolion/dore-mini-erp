# DDR-crm-integracion-whatsapp-cloud-api-pantalla-de-integracion-whatsapp: Pantalla Configuración → Integraciones → WhatsApp

**Estado:** Propuesto
**Task relacionado:** TASK-crm-integracion-whatsapp-cloud-api
**Fecha:** 2026-11-27

## Contexto
El administrador conecta el número de WhatsApp de su empresa, comprueba que funciona y ve el estado de sus plantillas. Es una pantalla de configuración de uso infrecuente, en un menú nuevo bajo Configuración.

## Pantallas/flujos afectados
- Menú: Configuración → **Integraciones → WhatsApp** (`/pocketbiz/settings/integrations/whatsapp`, entrada en `assets/data/routes.json` y claves i18n es/en/pt).
- Página única con tres bloques: **Conexión**, **Mensaje de prueba**, **Plantillas**.

## Componentes/patrones elegidos
- Plantilla «Formulario de configuración con pestañas» (`features/settings/pages/module-settings`, design-system §5) para el bloque Conexión; plantilla «Configuración con listados en pestañas y diálogo» (`inventory-configuration`) para la lista de plantillas. Sin componentes nuevos de Oreva.
- **Conexión** (Reactive Form): WABA ID, Phone number ID, nombre de la variable del token (`secret_ref`), nombre de la variable del App Secret (`app_secret_ref`); ambos deben empezar con el **prefijo de la empresa** (`WHATSAPP_<12 hex>_`, lo devuelve la API como `secret_ref_prefix`), que la pantalla muestra como ayuda y valida al escribir. Solo lectura con botón «Copiar»: **URL del webhook** y **verify token**, más un recordatorio con el enlace a la guía de configuración en Meta. Insignia de estado (Conectada / Con error / Sin configurar) con la razón del error (token expirado, firma, etc.). Los secretos **nunca se escriben ni se muestran**: solo se nombra la variable.
- **Enviar mensaje de prueba**: campo de teléfono (normalizado) + botón; el resultado (enviado / error de Meta con motivo) se muestra en un aviso. Dentro de la ventana no aplica: la prueba usa plantilla aprobada (`hello_world` o la elegida de un `ng-select`).
- **Plantillas**: tabla (nombre, idioma, categoría, estado con badge: aprobada = éxito, rechazada = peligro, pausada = advertencia, pendiente = neutro, fecha de sincronización) y botón «Sincronizar».
- Badges, botones y tokens del sistema de diseño (§2-3).

## Alternativas consideradas
- Asistente por pasos (wizard): descartado, son cuatro campos y la mayor parte del trabajo ocurre en Meta; se cubre con la guía enlazada.
- Aceptar el token en un campo de texto: descartado por la regla «nunca en texto plano en la BD» (ADR).

## Comportamiento por privilegio/estado
- Estados: cargando, sin conexión (formulario vacío con la guía), conectada, con error, sincronizando, sin plantillas (vacío con explicación), error de red.
- Solo el rol administrador ve el menú y puede guardar/probar/sincronizar; **el backend lo impone** (403 para otros roles) y aísla por `company_id`; el frontend solo oculta.
- Accesibilidad: las pestañas siguen el patrón de teclado de WAI-ARIA (una sola parada con Tab, flechas/Inicio/Fin cambian de pestaña); «Copiar» anuncia el resultado en una región `aria-live` y avisa si el portapapeles no está disponible.
- Guardar con cambios de WABA/phone_number_id pide confirmación (cambia el remitente).

## Consecuencias
- Menú «Integraciones» queda como contenedor para futuras integraciones.
- Hasta que exista un gestor de secretos, el alta requiere que quien despliega cree las variables de entorno (se indica en la pantalla).
