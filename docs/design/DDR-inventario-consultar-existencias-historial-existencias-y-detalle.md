# DDR-inventario-consultar-existencias-historial-existencias-y-detalle: Existencias con filtros y detalle por producto y almacén

**Estado:** Propuesto
**Task relacionado:** TASK-inventario-consultar-existencias-historial
**Fecha:** 2026-10-28

## Contexto
Existencias (PB-INV-003) es una lista mínima. La persona necesita buscar un producto, ver su saldo actual en cada almacén, distinguir saldos cero y negativos, y entender por qué cambió el stock sin salir del producto.

## Pantallas/flujos afectados
1. **Existencias** (`/pocketbiz/inventory/stock`): se amplía con buscador y filtros.
2. **Detalle de existencia** (`/pocketbiz/inventory/stock/:productId/:warehouseId`): nueva.
3. **Movimientos** (`/pocketbiz/inventory/movements`): la lista de PB-INV-004 recibe el filtro prellenado desde Existencias y el detalle (sin cambios de diseño; se corrige que un producto prellenado siempre aparezca en el selector, REV-09).

## Componentes/patrones elegidos
- **Existencias — plantilla Lista** (design-system §5; tabla Bootstrap apilada `_inventory-table.scss`, como hoy). Cabecera: buscador por nombre de producto (`search-field`, `label` + `aria-label`), y fila de filtros: Almacén (`form-select`, «Todos los almacenes» = solo activos; se listan también los inactivos), Estado del producto (Activos por defecto / Inactivos / Todos) y Saldo (Todos / Con saldo cero / Con saldo distinto de cero / Con saldo negativo); «Limpiar filtros». Botón «Registrar apertura» se mantiene en la cabecera.
- **Columnas:** Producto (enlace en negrita al detalle; badge `badge-outline` «Inactivo» si aplica), Almacén, Unidad base, Existencia (cantidad alineada a la derecha; si es negativa, texto rojo `text-danger` **y** badge con texto «Negativo»; si es 0, texto normal «0»), Acciones (ver detalle, «Movimientos»). No hay «disponible», «reservado» ni valor.
- **Detalle — plantilla Detalle** (design-system §5; `.card` con `h4` = nombre del producto, `dl.row`): Producto, Estado (Activo/Inactivo), Almacén (+ «Inactivo» si lo es), Unidad base, Existencia actual (con el mismo tratamiento del negativo). Acciones bajo los datos: **Ver movimientos** (primario, abre la lista de movimientos prefiltrada), **Registrar apertura** (solo si el producto está activo, el almacén está activo y el par no tiene movimientos; si no cumple, no se muestra y una nota `small.text-muted` explica: «Ya tiene movimientos; las correcciones se hacen con un ajuste.» o «Producto o almacén inactivo.»), **Volver** (`btn-light`). «Registrar ajuste» no se muestra (fuera de alcance, sin alta manual).
- **Historial en el detalle:** sección «Historial de movimientos» con tabla (Fecha y hora, Tipo con badge, Entrada, Salida, Referencia, Origen) reutilizando la presentación de la lista de movimientos, limitada al producto y almacén, 10 por página con `ngb-pagination`, más reciente primero, y enlace «Ver detalle» a cada movimiento (de donde se abre el documento de origen). Un par sin movimientos muestra saldo **0** y «Sin movimientos para este producto en este almacén.» (no error). Para filtrar por fecha o tipo, «Ver movimientos» lleva a la lista completa.
- **Estados** (design-system §4): cargando («Cargando…»), vacío («No hay productos que coincidan con los filtros.»), error de servidor (`small.text-danger` + «Reintentar»), 404 en detalle («Existencia no encontrada.» con enlace a Existencias).
- **Accesibilidad:** cada filtro con `label`; el saldo negativo se identifica por texto además del color; encabezados de tabla textuales.

## Alternativas consideradas
- **`ngx-datatable` en vez de tabla Bootstrap:** la lista de movimientos lo usa, pero Existencias ya es tabla Bootstrap apilada (móvil); cambiarla no aporta. Se mantiene.
- **Mostrar solo pares con movimientos:** no cumple «un producto sin movimientos tiene saldo cero» ni el filtro de saldo cero.
- **Historial con filtros de fecha/tipo dentro del detalle:** duplica la lista de movimientos; se enlaza a ella.
- **Botón «Registrar ajuste» deshabilitado:** descartado por el usuario (fuera de alcance).

## Comportamiento por privilegio/estado
Solo el administrador de la empresa; con Inventario deshabilitado las rutas redirigen (`moduleGuard`) y la API responde 403. El frontend no es la barrera: el servidor filtra por empresa, responde 404 a ids ajenos y la apertura se valida de nuevo en el backend (rechaza pares con historial).

## Consecuencias
Se agrega al design-system el patrón «Detalle con historial embebido». Deuda: sin ajustes; orden fijo por nombre de producto y almacén.
