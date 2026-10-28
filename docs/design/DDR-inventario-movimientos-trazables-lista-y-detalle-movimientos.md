# DDR-inventario-movimientos-trazables-lista-y-detalle-movimientos: Lista y detalle de movimientos de inventario

**Estado:** Propuesto
**Task relacionado:** TASK-inventario-movimientos-trazables
**Fecha:** 2026-10-28

## Contexto
El administrador consulta el libro de movimientos para saber quién, cuándo y por qué cambió el stock. Es de solo lectura: no se crean, editan ni eliminan movimientos desde la UI.

## Pantallas/flujos afectados
1. **Inventario → Movimientos** (`/pocketbiz/inventory/movements`): lista con filtros.
2. **Detalle de movimiento** (`/pocketbiz/inventory/movements/:id`).
3. **Menú Inventario**: nueva entrada «Movimientos» entre «Almacenes y unidades» y «Ajustes».

## Componentes/patrones elegidos
- **Lista** (design-system §5 Lista; referencia `expense-list`): `.card` con `h4` «Inventario › Movimientos», barra de filtros y tabla `ngx-datatable` con paginación del servidor. Filtros: rango de fechas (dos `input type=date` «Desde»/«Hasta»), Producto (`form-select` con los primeros 100 productos; el `ng-select` con búsqueda queda como mejora), Almacén (`form-select`), Tipo (Todos/Entrada/Salida) y Origen (Todos/Pedido de venta/Recepción de compra/Ajuste de inventario/Sin documento); botón «Limpiar». Sin botón «+» (no hay alta).
- **Columnas:** Fecha y hora, Referencia, Producto, Almacén, Tipo (badge `col-green` Entrada / `col-orange` Salida), **Entrada** y **Salida** como columnas separadas (la cantidad aparece en la que corresponde, la otra con «—»; alineadas a la derecha), Unidad (abreviatura), Origen (etiqueta de la clase y el id del documento; la referencia propia va en su columna) y la acción «Ver detalle» (icono ojo). Un movimiento revertido lleva además badge `col-grey` «Revertido» junto al tipo. Sin Editar ni Eliminar. Orden: más reciente primero.
- **Detalle** (design-system §5 Detalle; referencia `expense-detail`): `dl` con Identificador, Estado (badge Confirmado/Revertido), Empresa (de la sesión), Producto, Almacén, Tipo, Cantidad con unidad, Fecha y hora, Usuario, Referencia, Motivo y Origen. «Origen» muestra la clase y la referencia; si el servidor indica `available` y existe pantalla de destino (hoy `sales_order` → `/pocketbiz/sales/orders/:id`) se muestra un enlace «Abrir documento de origen»; si el módulo está deshabilitado o no hay pantalla, se muestra solo el texto (sin enlace). Sección «Contramovimientos» con enlaces al movimiento que lo revierte o al que este revierte. Botón «Volver».
- **Estados** (design-system §4): cargando (`loadingIndicator`), vacío («Sin movimientos para los filtros elegidos.»), error de servidor (`alert alert-danger` con reintento), 404 en detalle («Movimiento no encontrado.» con enlace a la lista).
- **Accesibilidad:** `label` en cada filtro, columnas con encabezados textuales, el badge de tipo con texto (no solo color).

## Alternativas consideradas
- **Columna única «Cantidad» con signo:** descartada, el requerimiento pide entrada y salida separadas.
- **Mostrar el saldo en la lista:** no pedido; queda para la historia de existencias.
- **Tabla Bootstrap simple en vez de `ngx-datatable`:** válida en listas cortas, pero este listado crece sin límite y requiere paginación del servidor, como Gastos.

## Comportamiento por privilegio/estado
Solo el administrador de la empresa; con Inventario deshabilitado la ruta se redirige (`moduleGuard`) y la API responde 403. El enlace al origen se oculta con el módulo propietario deshabilitado (`available=false`), pero la barrera real es la API de ese módulo: abrir la URL de otro módulo deshabilitado sigue bloqueado por sus propias reglas. El frontend no es la barrera de seguridad: el servidor filtra por empresa y responde 404 a ids ajenos.

## Consecuencias
Se añade el patrón «lista de solo lectura con filtros» a `design-system.md` §5. Deuda: el enlace al origen solo existe para pedidos de venta hasta que existan pantallas de compras y ajustes; filtro de producto con carga bajo demanda (sin resolver nombres de productos eliminados, que no existen: los productos no se borran).
