# DDR-confirmar-cancelar-compras-detalle-y-dialogos: Detalle de compra con pestaña «Resumen», acciones por estado y diálogos

**Estado:** Propuesto
**Task relacionado:** TASK-confirmar-cancelar-compras
**Fecha:** 2026-10-30

## Contexto
PB-COM-003 pide que el detalle de la compra (hoy una tarjeta `dl` + tabla, `purchase-detail.component.html`) muestre el estado documental, de recepción y de pago, ofrezca acciones según el estado y tenga dos diálogos: confirmar (resumen + aviso) y cancelar (motivo obligatorio). Referencias: plantilla **Detalle** y «Detalle con historial embebido» de `docs/design/design-system.md` §5; `DDR-ventas-inventario-salida-al-entregar-dialogo-entrega-y-detalle` (diálogo con `NgbModal`) y `order-detail` (cancelación con motivo).

## Pantallas/flujos afectados
- **Detalle** `/purchases/:id`: pasa a tener navegación por pestañas con la pestaña **«Resumen»** (única por ahora; las siguientes tasks añadirán «Recepciones» y «Pagos»).
- **Diálogo «Confirmar compra»** y **diálogo «Cancelar compra»** (nuevos).
- **Lista** `/purchases`: el badge de Estado y, en Acciones, «editar» solo para borradores.

## Componentes/patrones elegidos
**Detalle** (plantilla Detalle, `ngbNav` con `nav-tabs` como en Configuración):
- `h4` «Compra COM-XXXXXXXX» (referencia interna) con el badge de **Estado** al lado: Borrador (`col-orange`), Confirmada (`col-green`), Cancelada (`col-red`) mediante un `getPurchaseStatusClass()` junto a `PURCHASE_STATUS_LABELS`.
- Pestaña «Resumen»: `dl.row` con Referencia interna, Proveedor (con «Inactivo» si aplica), Fecha de compra, Referencia externa («Sin referencia»), Estado documental, Estado de recepción («Sin recibir», «Recibida parcialmente», «Recibida»), Estado de pago («Sin pagar», «Pago parcial», «Pagada»), Moneda, Notas («Sin notas»), Creada/Actualizada y, **solo si está confirmada**, «Confirmada el»; **solo si está cancelada**, «Cancelada el» y «Motivo de cancelación». Después, la tabla de productos con el Total (igual que hoy).
- **Barra de acciones** bajo la tabla, derivada de `allowed_actions` del servidor (no de reglas copiadas):
  - Borrador: **Editar** (`btn-primary`, enlace), **Confirmar** (`btn-success`), **Cancelar compra** (`btn-outline-danger`), **Volver**.
  - Confirmada: **Registrar recepción** y **Registrar pago** (`btn-primary` deshabilitados, con `small.text-muted` «Disponible próximamente»); **Cancelar compra** solo si `allowed_actions` incluye `cancel`; si no, texto `small.text-muted` «No se puede cancelar: ya tiene recepciones o pagos.» No hay «Editar».
  - Cancelada: sin acciones (solo **Volver**). Solo lectura.
- Una compra confirmada **no** muestra ningún texto ni valor de existencias; el estado de recepción dice «Sin recibir». Un `small.text-muted` aclara «Confirmar no modifica las existencias; el stock cambia al recibir la mercadería.» (solo al confirmar o en la confirmada).
- Mientras corre una acción: botones deshabilitados y «Procesando…». Éxito: `toastr` («Compra confirmada» / «Compra cancelada») y el detalle se actualiza con la respuesta. Error: `toastr.error` con el mensaje del servidor; si el servidor responde 400/409 por un cambio concurrente, se vuelve a leer la compra.

**Diálogo «Confirmar compra»** (`NgbModal`, `backdrop: 'static'`, patrón `DeliveryDialogComponent`): título «Confirmar compra»; resumen en `dl` (Proveedor, Fecha, N.º de productos, Total con `MoneyPipe`) y `alert alert-warning`: «Al confirmar, los precios y las cantidades quedan bloqueados y la compra ya no se podrá editar.» Más la nota de existencias. Botones **Confirmar compra** (primario) y **Volver** (`btn-light`).

**Diálogo «Cancelar compra»** (`NgbModal`): título «Cancelar compra», texto «La compra quedará cancelada y en solo lectura.» (si está confirmada, además «Se cancela sin recepciones ni pagos.»), `textarea` «Motivo de la cancelación*» (maxlength 500, contador), error bajo el campo si el servidor lo devuelve. El botón **Cancelar compra** (`btn-danger`) permanece **deshabilitado hasta que el motivo, recortado, no esté vacío**; **Volver** cierra sin cambios.

Estados (design-system §4): cargando (`Cargando…`), error de carga (aviso y regreso a la lista, como hoy), acción en curso, éxito con toast, error visible. El reflejo del estado en los botones sale del servidor.

## Alternativas consideradas
1. **SweetAlert para ambos diálogos** (como `askCancelReason`): su validación aparece al pulsar, y no deja el botón deshabilitado como pide la historia («antes de habilitar la confirmación»). Descartada; `NgbModal` con formulario reactivo lo resuelve y es el patrón del diálogo de entrega.
2. **Pestañas «Recepciones» y «Pagos» vacías ahora**: descartadas, mostrarían pantallas sin función; solo «Resumen», y las tasks siguientes añaden pestañas.
3. **Ocultar «Registrar recepción/pago» hasta que existan**: la historia los lista para Confirmado; se muestran deshabilitados y explicados para no prometer algo que no responde.
4. **Calcular en el cliente cuándo se puede cancelar**: descartada; el servidor entrega `allowed_actions`, el cliente solo lo refleja (y el backend valida igual).

## Comportamiento por privilegio/estado
Solo administradores de empresa con el módulo `purchases` habilitado acceden (`moduleGuard`). Estado → acciones: `draft` → Editar/Confirmar/Cancelar; `confirmed` → Cancelar (solo sin actividad), Recepción/Pago deshabilitados; `cancelled` → ninguna. **El frontend no es la barrera**: el backend repite cada regla (proveedor activo e ítem ≥ 1 al confirmar, motivo y ausencia de recepciones/pagos al cancelar, edición solo en borrador) y responde 400/404/409.

## Consecuencias
- El detalle queda preparado para añadir pestañas de Recepciones y Pagos; mientras tanto la barra de pestañas tiene una sola.
- Dos botones deshabilitados «próximamente» son deuda visual aceptada hasta las tasks de recepción y pago.
- Se propone en `docs/design/design-system.md` §5 una nota en «Detalle»: detalle con pestañas y diálogos `NgbModal` de confirmación/cancelación con botón habilitado por motivo; sin componente compartido nuevo.
