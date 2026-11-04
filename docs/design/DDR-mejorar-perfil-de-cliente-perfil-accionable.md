# DDR-mejorar-perfil-de-cliente-perfil-accionable: Perfil de cliente con contacto accionable, resumen de compras y saldo

**Estado:** Propuesto
**Task relacionado:** TASK-mejorar-perfil-de-cliente
**Fecha:** 2026-11-04

## Contexto
El perfil actual es una ficha de registro (`dl.row` + tabla simple). Quien lo usa —dueño o personal de un negocio pequeño— quiere llamar o escribir al cliente, saber cuánto y cuándo compró, si debe dinero y abrir un pedido concreto. Los datos ya existen (ver TASK, Investigación).

## Pantallas/flujos afectados
- `/pocketbiz/customers/:id` (detalle de cliente) y su componente de historial.
- `/pocketbiz/sales/orders/new` (solo: llega con el cliente preseleccionado desde el perfil).

## Componentes/patrones elegidos
Plantilla **Detalle** (`design-system.md` §5) con estas adaptaciones:

1. **Tarjeta de identidad.** `.card` con `card-header`: `h4` = nombre + badge Activo/Inactivo (`badge-outline col-green|col-red`) a la izquierda y las acciones a la derecha (`d-flex flex-wrap gap-2`): **Nuevo pedido** (`btn-primary`), **Editar** (`btn-light`), **Desactivar/Activar** (`btn-warning`). Se elimina el botón «Volver» (el breadcrumb ya lo cumple). Cuerpo: `dl.row` solo con Teléfono, Correo y Notas (sin «Nombre» duplicado).
2. **Contacto accionable.** Teléfono como enlace `tel:` más botón «WhatsApp» (`btn btn-light btn-sm`, `target="_blank" rel="noopener"`, `aria-label` y `title`); correo como `mailto:`. Sin dato: «Sin teléfono» / «Sin correo» (texto de relleno «Sin …» de la plantilla, en lugar de «—»).
3. **Tira de resumen** con `app-report-card` (patrón de cifras de Dashboard): **Última compra** (fecha), **Pedidos** (cantidad), **Total comprado** (`money`) y **Saldo pendiente** (`money`; `text-danger` solo si > 0, siempre con texto, nunca solo color), con `<small class="text-muted">` de apoyo («Sin contar cancelados»; «Al día» cuando el saldo es 0). `row` con `col-6 col-lg-3`.
4. **Historial** (`.card`, `h4` «Historial de compras»), tabla Bootstrap simple apilada en móvil (patrón `_inventory-table.scss`) con columnas: **Pedido** (código como enlace al detalle, `fw-semibold`), **Fecha**, **Total**, **Pagado**, **Saldo** (importes alineados a la derecha con `money`), **Entrega** (`app-order-status-badge`) y **Pago** (`app-payment-status-badge`). Pedidos cancelados: fila atenuada (`text-muted`), saldo «—», no cuentan en las cifras. Cabecera del card: enlace «Ver todos los pedidos» a `/pocketbiz/sales/orders?customer=<id>&customer_name=<nombre>`. Pie: «Mostrando X de Y pedidos» (X cargados, Y total).
5. **Pie de auditoría.** «Creado … · Actualizado …» como `<small class="text-muted">` bajo las tarjetas.

## Alternativas consideradas
- **Mantener Editar como botón primario (plantilla literal):** descartada: la acción de negocio del cliente es crear su siguiente pedido; se justifica la desviación como única acción primaria (regla «una por pantalla» se conserva).
- **Pestañas Resumen/Historial:** más complejas, ocultan el historial; con un historial corto no aportan.
- **Gráficos de frecuencia o ticket promedio:** descartado: con pocos pedidos inducen a error y no están respaldados por datos agregados.
- **Agregados calculados en servidor:** más exacto para historiales largos pero requiere API nueva; se difiere (ADR historial-compras lo prevé si el perfil lo necesita).

## Comportamiento por privilegio/estado
- **Cargando:** «Cargando…» en la tarjeta y «Cargando historial…» en el historial; las cifras no se muestran hasta tener los datos (no 0).
- **Error del historial:** mensaje visible en la tarjeta de historial; el perfil y las acciones siguen disponibles; las cifras no se muestran.
- **Cliente sin pedidos:** cifras «Sin compras» / 0 / `Bs 0.00` / `Bs 0.00`; el historial dice «Este cliente aún no tiene pedidos.» con botón «Crear primer pedido» (si aplica «Nuevo pedido»).
- **Cliente inactivo:** no se muestra «Nuevo pedido» ni «Crear primer pedido» (el selector del formulario solo lista clientes activos); el historial sigue visible.
- **Historial parcial** (Y > X): las cifras se calculan con los X pedidos cargados y se avisa: «Calculado con los X pedidos más recientes».
- **Módulo Pedidos deshabilitado:** se ocultan las acciones y enlaces a pedidos.
- **Móvil (<576 px):** acciones en varias líneas, cifras 2×2, cada pedido como bloque (código + fecha + total, luego badges).
- **Accesibilidad:** `<caption>` oculta visualmente en la tabla, `scope="col"`, botones/enlaces solo icono con `aria-label` y `title`, estados siempre con texto, objetivos táctiles ≥ 44 px en móvil.
- **Seguridad:** el frontend no es barrera; el backend sigue aplicando permisos y aislamiento por empresa en `/api/customers/` y `/api/orders/`.

## Consecuencias
- Desviación documentada: «Nuevo pedido» como acción primaria y «Editar» como secundaria (distinto de `product-detail`). Si se adopta como patrón para detalles de entidades con actividad, proponer su inclusión en `design-system.md` (§5 Detalle).
- Las cifras son parciales en historiales de más de 100 pedidos (aviso explícito) hasta que exista un agregado en servidor.
- `product-detail` y demás detalles quedan con el patrón anterior (inconsistencia visual aceptada).
