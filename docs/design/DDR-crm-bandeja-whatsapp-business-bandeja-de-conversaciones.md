# DDR-crm-bandeja-whatsapp-business-bandeja-de-conversaciones: Pantalla «Bandeja» de dos paneles

**Estado:** Propuesto
**Task relacionado:** TASK-crm-bandeja-whatsapp-business
**Fecha:** 2026-11-28

## Contexto
El vendedor necesita atender chats de WhatsApp, saber quién es el responsable y vincular la conversación a un contacto y a una oportunidad sin salir de CRM. No existe en `docs/design/design-system.md` una plantilla de bandeja/chat.

## Pantallas/flujos afectados
Ruta nueva `/pocketbiz/crm/inbox`, entrada de menú **CRM → Bandeja** (`MENUITEMS.CRM.LIST.INBOX`), tras «Por contactar».

**Pantalla Bandeja** (`features/crm/pages/crm-inbox`):
- **Panel izquierdo — lista**: filtros «Mías / Sin asignar / Todas» (botones segmentados), búsqueda por teléfono o nombre; cada fila: nombre o teléfono, vista previa del último mensaje, hora relativa, insignia de responsable y de «Ventana cerrada».
- **Panel derecho — conversación**: cabecera (contacto, teléfono, responsable, oportunidad), historial en burbujas (entrante/saliente; estado ✓ enviado, ✓✓ entregado/leído; «Falló» con motivo y botón **Reenviar**), caja de respuesta.
- **Acciones en la cabecera**: «Asignar» (selector de usuario, incluye «Sin responsable»), «Vincular contacto» (buscar cliente o prospecto; si no hay, «Crear prospecto» reutiliza `lead-dialog`), «Vincular oportunidad» (lista de oportunidades abiertas del contacto) y «Crear oportunidad» (reutiliza `opportunity-dialog` con el contacto precargado).
- **Caja de respuesta**: con ventana abierta, texto libre; con ventana cerrada, se deshabilita el texto, se explica por qué y se ofrece «Enviar plantilla» (selector de plantillas aprobadas).

## Componentes/patrones elegidos
Tokens, botones, insignias de estado y estados vacío/cargando/error de `design-system.md` §2-4. Lista y filtros siguen la plantilla «Lista» (§5) en el panel izquierdo; los diálogos de vincular/asignar siguen el patrón de diálogos CRM existentes (`opportunity-dialog`, `convert-lead-dialog`) con `[formGroup]` y botones Cancelar/Guardar. No se usa componente nuevo de la plantilla Oreva.
**Plantilla nueva propuesta para `design-system.md` §5: «Bandeja de conversaciones (lista + hilo)»** con la anatomía anterior.
**Responsive**: desde `lg` (992 px) dos paneles; por debajo, un panel a la vez (lista → al elegir una conversación se muestra el hilo con botón «Volver a la lista»).
**Actualización**: el hilo consulta mensajes nuevos cada 10 s mientras la pestaña está visible (el temporizador se cancela al salir); sin tiempo real.

## Alternativas consideradas
- **Dos pantallas (lista y detalle por ruta)**: más simple pero obliga a navegar por cada respuesta; peor para atender varios chats. Descartada en escritorio; en móvil se logra el mismo efecto con un panel a la vez.
- **Vincular desde el Kanban de oportunidades**: la tarjeta pide la acción en la bandeja; el Kanban podrá mostrar el chat más adelante.

## Comportamiento por privilegio/estado
- Estados: cargando (lista y hilo), vacío («Aún no hay conversaciones. Cuando un cliente escriba a tu WhatsApp aparecerá aquí.»; sin conexión activa: aviso con enlace a Configuración → WhatsApp), error con «Reintentar», éxito con aviso breve al asignar/vincular.
- Texto libre solo con ventana abierta; plantillas solo aprobadas; botón Reenviar solo en mensajes salientes `failed`.
- **El frontend no es la barrera**: la empresa sale del usuario autenticado; el backend valida módulo `customers`, pertenencia a la empresa de usuario/cliente/prospecto/oportunidad, ventana de 24 h y estado del mensaje.
- Accesibilidad: lista con `role="listbox"`/botones nativos, foco al hilo al abrir, nuevas burbujas anunciadas con `aria-live="polite"`, estado del mensaje con texto además de icono.

## Consecuencias
Una plantilla nueva en el sistema de diseño. Deuda aceptada: sin «no leídos», sin adjuntos multimedia (se muestra el tipo, p. ej. «[Imagen]») y sin tiempo real.
