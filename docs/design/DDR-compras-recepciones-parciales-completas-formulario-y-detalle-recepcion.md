# DDR-compras-recepciones-parciales-completas-formulario-y-detalle-recepcion: Pestaña «Recepciones», formulario de recepción y detalle de recepción

**Estado:** Propuesto
**Task relacionado:** TASK-compras-recepciones-parciales-completas
**Fecha:** 2026-10-30

## Contexto
PB-COM-004 permite registrar recepciones parciales o completas desde el detalle de una compra confirmada. Hoy el detalle (`purchase-detail.component.html`) tiene una sola pestaña «Resumen» y «Registrar recepción» deshabilitado. Referencias: `docs/design/design-system.md` §5 («Detalle con pestañas y acciones de ciclo de vida», «Formulario con líneas y paso de resumen», «Lista de solo lectura con filtros», «Detalle con historial embebido») y `DDR-confirmar-cancelar-compras-detalle-y-dialogos` (que anticipó las pestañas siguientes).

## Pantallas/flujos afectados
1. **Detalle de compra** `/pocketbiz/purchases/:id`: pestañas **«Resumen»** y **«Recepciones»**.
2. **Formulario de recepción** `/pocketbiz/purchases/:id/receipts/new` (nuevo).
3. **Detalle de recepción** `/pocketbiz/purchases/:id/receipts/:receiptId` (nuevo).
4. **Lista de Movimientos de inventario** (cambio mínimo): etiqueta «Entrada por compra» para entradas con origen `purchase_receipt`.

No se añade ninguna entrada al menú lateral; el acceso es siempre desde el detalle de la compra.

## Componentes/patrones elegidos

**Detalle de compra (plantilla Detalle con pestañas).**
- `ngbNav` con `nav-tabs` (pestañas «Resumen» y «Recepciones»; la activa se puede fijar con `?tab=receptions` para volver desde el formulario).
- *Resumen*: la tabla de productos de una compra **confirmada** suma las columnas **Recibida** y **Pendiente** (alineadas a la derecha, con la unidad); en borrador y cancelada no se muestran. El botón «Registrar recepción» de la barra de acciones deja de estar deshabilitado: se muestra si `allowed_actions` incluye `receive` (enlace `btn-primary` al formulario); con la compra totalmente recibida se reemplaza por `small.text-muted` «Compra recibida por completo». «Registrar pago» sigue deshabilitado («Disponible próximamente»). El aviso de la confirmada ya no dice que la recepción es «próxima»: «Confirmar no modifica las existencias; el stock cambia al registrar la recepción.»
- *Recepciones*: (a) `h5` «Avance de la recepción» con tabla Producto · Unidad · Comprada · Recibida · Pendiente y el badge del estado de recepción (`Sin recibir`/`Recibida parcialmente`/`Recibida`); (b) `h5` «Recepciones registradas» con tabla Bootstrap apilada (patrón historial embebido): **Referencia** (enlace al detalle), **Fecha**, **Estado** (badge `Confirmada` `col-green` / `Revertida` `col-orange`, siempre con texto), **Usuario**; botón «Registrar recepción» (`btn-primary`) a la derecha del título cuando `receive` está permitido. Vacío: «Aún no hay recepciones registradas para esta compra.» (para una confirmada sin recepciones) y, para borrador/cancelada, «Las recepciones se registran cuando la compra está confirmada.» Cargando: «Cargando…». Error: `alert alert-danger` con «Reintentar».

**Formulario de recepción (plantilla Formulario con líneas y paso de resumen, en dos pasos en la misma ruta).**
- Breadcrumb Compras › Compra COM-… › Registrar recepción. `card` con cabecera de campos:
  - **Fecha de recepción*** (`input type="date"`, por defecto hoy, `max` = hoy).
  - **Almacén*** (`form-select` con almacenes activos): se renderiza **solo** si Inventario está habilitado **y** hay al menos un producto con pendiente que controle stock (el servidor lo informa; ver ADR). Preselecciona el único activo o el predeterminado. Si no hay almacenes activos: `alert alert-warning` «No hay almacenes activos. Crea uno en Inventario › Configuración para recibir productos con control de stock.» y «Revisar» queda deshabilitado mientras haya líneas controladas con cantidad.
- Tabla de líneas (todas las líneas de la compra): **Producto** (solo lectura, con marca «Controla stock» `small.text-muted` cuando aplica el almacén), **Unidad**, **Comprada**, **Recibida**, **Pendiente**, **A recibir** (`input type="number"`, `step` según fracciones de la unidad, 3 decimales como máximo, vacío = 0). Líneas con pendiente 0: campo deshabilitado y texto «Completa». Enlace «Recibir todo lo pendiente» sobre la tabla que rellena cada línea con su pendiente.
- Validación en el cliente (el servidor repite cada regla): negativo, no numérico, más decimales de los permitidos, fracciones en unidades enteras y mayor que el pendiente se muestran en `small.text-danger` bajo el campo y la fila se marca `table-warning`; «Revisar recepción» está deshabilitado si hay algún error o si ninguna línea tiene cantidad positiva (mensaje: «Indica una cantidad mayor a cero en al menos un producto.»). Las líneas con cantidad vacía o cero se omiten al enviar.
- **Paso Resumen**: `card` con `dl.row` (Compra, Proveedor, Fecha, Almacén si aplica, N.º de productos que se reciben) y tabla de solo lectura con las líneas a recibir (Producto, Unidad, A recibir, Pendiente después). Si hay productos controlados, `alert alert-info`: «Se registrará una entrada de existencias en <almacén> por cada producto con control de stock.» Botones: **Confirmar recepción** (primario; deshabilitado con «Registrando…» mientras envía) y **Volver a editar** (`btn-light`).
- El formulario genera `receipt_id` (UUID) al abrirse y lo reutiliza en cada reintento. Con cambios sin enviar, salir usa `unsavedChangesGuard`.
- Errores del servidor: 400 por línea o campo se muestran junto a su campo y regresan al paso de edición sin borrar lo escrito; 409 («La compra ya no admite recepciones», o cantidades que cambiaron por otra recepción) → `alert alert-warning`, se vuelven a leer las cantidades y se conserva lo escrito; error de red → `toastr.error` y botones rehabilitados.
- Éxito: `toastr` «Recepción REC-… registrada» y navegación a `/pocketbiz/purchases/:id?tab=receptions`, donde ya aparecen los pendientes y el estado actualizados.

**Detalle de recepción (plantilla Detalle).**
- `h4` «Recepción REC-XXXXXXXX» con badge de estado. `dl.row`: Compra (enlace a la compra), Proveedor, Fecha de recepción, Estado, Registrada por (usuario), Registrada el (fecha y hora) y **Almacén** solo si la recepción lo tiene.
- `h5` «Productos recibidos»: tabla Producto · Unidad · Cantidad recibida.
- `h5` «Movimientos de inventario» (patrón `stock-output-card` de Ventas): solo si Inventario está habilitado y la recepción generó entradas — tabla Producto · Almacén · Cantidad y enlace «Ver movimientos» a la lista de Movimientos filtrada por origen. Sin entradas (recepción documental) se muestra `small.text-muted` «Esta recepción no movió existencias.» únicamente cuando Inventario está habilitado; con Inventario apagado la sección no se renderiza.
- Acciones: **Volver a la compra** (`btn-light`). Sin acciones de edición ni de reversión (la recepción confirmada es inmutable en esta task).

**Lista de Movimientos.** Las entradas con origen `purchase_receipt` se etiquetan «Entrada por compra» (presentación, igual que «Salida por venta»); sin cambios de contrato.

Estados que cubre cada pantalla (design-system §4): cargando, vacío, error de validación, error de servidor, éxito.

## Alternativas consideradas
1. **Formulario en un diálogo `NgbModal`** (como la entrega de Ventas): descartada; la tabla de seis columnas con validación por línea y un paso de resumen no cabe bien en un diálogo y la historia pide «formulario y detalle de cada recepción».
2. **Una sola vista de un paso sin resumen:** descartada; la historia dice «completar cantidades, revisar y Confirmar», y confirmar genera movimientos de stock, así que corresponde la variante con resumen del sistema de diseño.
3. **Almacén por línea:** descartada por complejidad (supuesto H-02); un selector de cabecera cubre el caso común y las demás se registran en otra recepción.
4. **Mostrar siempre el selector de almacén (con Inventario activo):** descartada; la historia pide no exigirlo ni mostrarlo cuando no aplica (sin Inventario o sin productos controlados).
5. **Mostrar los pendientes solo en la pestaña Recepciones:** descartada; el Resumen también los muestra para quien no abre la pestaña.

## Comportamiento por privilegio/estado
- Solo administradores de empresa con el módulo `purchases` habilitado (`moduleGuard`). El almacén y los movimientos solo aparecen con Inventario habilitado.
- «Registrar recepción» solo en compras `confirmed` con pendiente (`allowed_actions` contiene `receive`). Borrador y cancelada no ofrecen la acción.
- **El frontend no es la barrera:** el backend vuelve a validar estado de la compra, pendientes por línea, fecha, almacén activo y control de stock, y responde 400/404/409. Abrir el formulario en una compra no recibible muestra el error del servidor.

## Consecuencias
- Un solo almacén por recepción puede obligar a registrar dos recepciones si los productos entran a almacenes distintos (deuda aceptada, H-02).
- El estado «Revertida» está en la tabla pero sin acción para producirlo en esta task (H-03): la UI lo soporta para cuando exista.
- Se propone en `docs/design/design-system.md` §5 una nota en «Detalle con pestañas…» y en «Formulario con líneas…» sobre estas variantes; sin componente compartido nuevo.
