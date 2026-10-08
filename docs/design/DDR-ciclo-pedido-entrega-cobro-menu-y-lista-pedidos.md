# DDR-ciclo-pedido-entrega-cobro-menu-y-lista-pedidos: Menú "Pedidos" y lista operativa de pedidos

**Estado:** Propuesto
**Task relacionado:** TASK-ciclo-pedido-entrega-cobro
**Fecha:** 2026-10-08

## Contexto
No existe ninguna pantalla de pedidos (`frontend/panel_admin/src/app/features/` solo tiene `products/` y `customers/`; `app.routes.ts` no tiene ruta de ventas). El menú (`src/assets/data/routes.json`) tiene "Dashboard", "Catálogo ▸ Producto" y "Cliente". REQ-SAL-014 pide una lista operativa con filtros mínimos (estado, estado de pago, fecha, cliente, canal) y orden por fecha relevante; el criterio de aceptación exige poder localizar pedidos **pendientes, entregados, cancelados y por cobrar**. REQ-SAL-016 exige que entrega y cobro se vean como dos ejes distintos. Ya hay un patrón aprobado y construido para listas: [DDR-clientes-mvp-menu-y-pantallas-cliente](DDR-clientes-mvp-menu-y-pantallas-cliente.md) y `features/customers/pages/customer-list/customer-list.component.html`. La plantilla no tiene roles (ver DDR del catálogo), así que no hay variación por privilegio.

## Pantallas/flujos afectados
1. **Menú lateral**: nueva entrada "Pedidos".
2. **Lista de pedidos** (`/sales/orders`): filtrar con atajos y filtros finos, ordenar, ir a crear y abrir el detalle (REQ-SAL-014, 015, 009 consulta por fecha prevista, 007 filtro por canal).

El formulario, el detalle y los pagos están en [DDR-ciclo-pedido-entrega-cobro-formulario-y-detalle-pedido](DDR-ciclo-pedido-entrega-cobro-formulario-y-detalle-pedido.md).

## Componentes/patrones elegidos

**Menú** — mismo mecanismo (`routes.json` + claves `MENUITEMS.*` en `assets/i18n/{en,es,de}.json`). Entrada de primer nivel **directa** "Pedidos" (`class: ""`, `path: "/sales/orders"`, icono feather `shopping-cart`, sin submenú), como "Dashboard" y "Cliente". Clave `MENUITEMS.ORDERS.TEXT` = "Pedidos" (es), "Orders" (en), "Bestellungen" (de). La ruta lleva el prefijo `sales/` (como `catalog/products`) para dejar espacio al módulo si más adelante se agregan pantallas.

**Lista** — copia estructural de `customer-list.component.html`: `ngx-datatable class="material"` con paginación externa (`ngx-datatable.html` de `panel_admin_doc`, ya usado en productos y clientes), cabecera con `table-search-area`, botón redondo "+" (`btn-primary rounded-button`) hacia `/sales/orders/new`, breadcrumb `Pedidos`. Cambios respecto a clientes:

- **Atajos de vista** (fila de botones `btn-group` de Bootstrap bajo el título): **Todos · Pendientes de entrega · Por cobrar · Entregados · Cancelados**. Cada atajo solo fija los filtros finos (no es un filtro aparte), así el usuario ve qué se aplicó y puede ajustarlo. Es lo que cubre el criterio "localizar pendientes, entregados, cancelados y por cobrar" con un clic.
- **Filtros finos** (una fila de controles `form-select`/`form-control` bajo los atajos): Estado de entrega (Todos / Nuevo / En preparación / Listo / Entregado / Cancelado), Estado de pago (Todos / Pendiente / Parcial / Pagado / Reembolsado), Canal (Todos / WhatsApp / Facebook / Instagram / Venta directa / Feria / Otro), Cliente (`ng-select` con búsqueda por nombre/teléfono, patrón de `src/app/forms/select-item`; opción "Sin cliente" no se ofrece como filtro en el MVP), y **Fecha**: un selector "Fecha de: Pedido | Entrega prevista" más "Desde" y "Hasta" con `input type="date"` (el control nativo que ya usa `forms/basic-form`; sin dependencia nueva de datepicker). Botón "Limpiar filtros".
- **Orden:** el usuario no ordena por columna (columnas `[sortable]="false"`, igual que clientes); el orden lo da el servidor y la lista lo explica con una línea de ayuda bajo la tabla ("Ordenado por fecha de pedido, más recientes primero" / "…por entrega prevista, más próximas primero" según el atajo). Propuesta: con "Pendientes de entrega" se ordena por entrega prevista ascendente (las más urgentes arriba, sin fecha al final); con el resto, por fecha de pedido descendente. El contrato de orden lo cierra arquitectura.
- **Columnas:** Pedido (fecha de pedido `dd/MM/yyyy` como enlace al detalle; si arquitectura define un código legible, se muestra debajo en gris), Cliente (nombre, o "Sin cliente" en gris), Canal, Entrega prevista (o "—"), Total, Saldo, **Entrega** (badge), **Pago** (badge), Acciones (Ver). Importes alineados a la derecha con formato `Bs 0.00`.
- **Dos badges separados y con icono**, para que los ejes no se confundan: Entrega con `fa-truck`, Pago con `fa-coins`. Clases existentes `badge-outline col-*` de la plantilla (ya usadas: `col-blue`, `col-orange`, `col-indigo`, `col-green`, `col-red`, `col-cyan`, `col-purple`):

  | Entrega | Color | Pago | Color |
  |---|---|---|---|
  | Nuevo | `col-blue` | Pendiente | `col-orange` |
  | En preparación | `col-orange` | Parcial | `col-cyan` |
  | Listo | `col-indigo` | Pagado | `col-green` |
  | Entregado | `col-green` | Reembolsado | `col-purple` |
  | Cancelado | `col-red` | | |

  Los colores se repiten entre ejes (naranja, verde): el icono y el encabezado de columna son lo que identifica el eje; el color nunca es el único portador de significado (el badge siempre lleva texto).
- **Saldo:** en rojo (`text-danger`) cuando es mayor a cero y el pedido no está cancelado; "—" en pedidos cancelados sin pagos; en un pedido **entregado con saldo** se acentúa para que "entregado y por cobrar" salte a la vista.
- **Acciones:** solo "Ver" (`fa-eye`, mismo estilo `btn-tbl-view`). Los cambios de estado, pagos y cancelación se hacen desde el detalle, donde el usuario ve el contexto completo; no se ponen acciones destructivas en la fila.
- **Estados de pantalla:** `loadingIndicator`; vacío "No hay pedidos que coincidan con los filtros." / "Aún no hay pedidos." con enlace a crear; errores de red con `toastr`. Al volver desde el detalle se conservan los filtros y la página (estado en la URL por query params) para no perder el contexto operativo.
- **Vista inicial:** atajo **Todos**, sin filtros; no se oculta ningún pedido por defecto (a diferencia de Clientes, REQ-SAL-014 no define un estado oculto por defecto).

## Alternativas consideradas
- **Atajos + filtros finos vs. solo filtros finos.** Solo filtros obligan a combinar dos o tres controles para "por cobrar" (estado de pago ≠ pagado y no cancelado), la consulta más frecuente del negocio. Atajos añaden una fila de botones pero bajan los clics. **Ambos.**
- **Atajos como pestañas (`nav-tabs`) con contador vs. botones.** Pestañas con contador exigen consultas de conteo por cada una y sugieren que las categorías son excluyentes ("por cobrar" y "entregados" se solapan). **Botones de grupo, sin contador.**
- **Una sola columna "Estado" con dos badges vs. dos columnas.** Dos badges en una celda ahorran ancho pero impiden leer cada eje de un vistazo y dificultan comparar filas. **Dos columnas.**
- **Rango de fechas con datepicker de la plantilla (`ui/datepicker`, ng-bootstrap) vs. `input type="date"`.** El datepicker mejora la experiencia pero añade apertura de popup y estilos; para un filtro de dos fechas el control nativo basta y es el que ya usa la plantilla en formularios. **Nativo.**
- **Ordenar por columna (encabezados clicables) vs. orden fijo por atajo.** Ordenar por columna exige que el contrato soporte múltiples campos de orden; el requisito pide "ordenarse por fecha relevante", singular. **Orden fijo por vista.** Si se pide después, es un cambio aditivo.
- **Entrada de menú directa vs. grupo "Ventas ▸ Pedidos".** El grupo imita "Catálogo", pero el módulo hoy tiene una sola pantalla de entrada (los cobros se operan desde el pedido). **Directa**; se convierte en grupo si aparecen más pantallas (p. ej. un tablero de cobros).
- **Acciones de estado en la fila (marcar listo, entregar) vs. solo en detalle.** Aceleran una operación frecuente pero ponen en un clic acciones con efecto (entregar, cancelar) sin contexto y multiplican los casos de error en la tabla. **Solo en detalle** en el MVP.

## Comportamiento por privilegio/estado
- **Privilegios:** no existen roles; todo usuario autenticado ve y hace todo. Esto es solo UX: la verificación real corresponde al backend (`IsAuthenticated` por defecto, `backend/config/settings/base.py:75-77`) y a `delivery-architect` si se quisiera algo más fino. **El frontend no es la barrera de seguridad.**
- **Estado de los pedidos en la lista:** los cancelados siguen visibles con badge rojo y sus pagos/saldo; no se ocultan.
- **Textos:** contenido de pantallas en español; solo el menú pasa por `translate` (igual que Catálogo y Cliente).

## Consecuencias
- Más simple: reutiliza `ngx-datatable`, `ng-select`, `input type="date"`, `toastr` y los estilos de acciones de tabla; sin dependencias nuevas de UI; menú de una sola entrada.
- Pendiente para arquitectura (no se decide aquí): contrato de filtros (`status`, `payment_status`, `channel`, `customer_id`, rango de fechas y **qué fecha** filtra), contrato de orden por vista, si la lista devuelve `payment_status`, `balance` y `paid_total` ya calculados (la lista los muestra), dónde vive el estado de pago derivado para poder filtrarlo y paginar, si el pedido tiene un código legible, y qué significa exactamente "por cobrar" (propuesta: pago Pendiente o Parcial, excluyendo cancelados; sujeto a la Specification).
- Deuda aceptada: `Page<T>` y los estilos `btn-tbl-*` están duplicados entre `products` y `customers`; `sales` sería la tercera feature que los necesita, que es el umbral que el task de clientes fijó para extraerlos a `shared/`. Es decisión de plan; este DDR no la toma.
- Inconsistencia que quedaría si no se actualiza: la sección "Historial de compras" del perfil de cliente (ver el otro DDR).
