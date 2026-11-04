# DDR-mejorar-ux-catalogo-productos-servicios-lista-detalle-formulario: Usos visibles, resumen por cifras y pantallas hermanas en Catálogo

**Estado:** Propuesto
**Task relacionado:** TASK-mejorar-ux-catalogo-productos-servicios
**Fecha:** 2026-11-04

## Contexto
Productos y Servicios muestran datos como filas Sí/No y no dicen para qué sirve cada producto. Un producto puede **venderse**, **comprarse** o **usarse para producir otro** (insumo). Producción no existe aún (fuera del MVP), así que «insumo» se deriva de la categoría (materia prima, empaque, intermedio); no hay dato nuevo ni receta. Servicios es hermano de Productos pero se ve distinto (botones grises, buscador sin estilo, etiquetas distintas).

## Pantallas/flujos afectados
Lista, detalle y formulario de **Productos** (`features/products`) y de **Servicios** (`features/services`). Sin cambios de rutas ni de API.

## Componentes/patrones elegidos
Base: plantillas Lista, Formulario y Detalle de `design-system.md` §5, badges outline de §3, `money`, botones de tabla de `_table-actions.scss`.

### Patrón nuevo: «Usos del producto» (`app-product-uses`)
Componente presentacional en `shared/components/product-uses` (se usará en 3 pantallas de `products`; Inventario podrá migrar después). Entrada: `canSell`, `canBuy`, `category`. Chips `badge-outline` **siempre con texto**:

| Chip | Color | Cuándo |
|---|---|---|
| Vendible | `col-green` | `canSell` |
| Comprable | `col-blue` | `canBuy` |
| Insumo | `col-purple` | categoría `raw_material`, `packaging` o `intermediate` |
| Sin usos | `col-grey` | ninguno de los anteriores |

«Insumo» lleva `title`/texto de apoyo «Según su categoría: se puede usar para producir otros productos». Vocabulario igual al de Inventario («Vendible», «Comprable», «Sin usos»), lo que reemplaza «Compra»/«Venta».

### Lista de Productos
- Cabecera como hoy (buscador con icono, filtros, «+»). Corregir el solapamiento del chevron de los `select` (padding derecho) y mantener los tres filtros; el filtro **Uso** conserva «Se vende / Se compra» (el backend filtra por una categoría, no por insumo; el filtro de categoría ya cubre insumos).
- Columnas: **Nombre** (enlace en negrita) · **Categoría** · **Usos** (`app-product-uses`) · **Precio** (`money`, alineado a la derecha, vacío «—» si no se vende) · **Estado** (badge) · **Unidad base** (solo con Inventario; abreviatura, «—» si no controla stock) · **Acciones**. Se elimina la columna «Controla stock» Sí/No (la unidad base ya lo indica y el dato sigue en el detalle).
- Acciones: se mantienen ver/editar/activar-desactivar con los botones estándar (§3) para no desviarse del sistema; el cambio es que el nombre sigue siendo el enlace principal.
- Filas inactivas con texto atenuado (`text-muted`) además del badge.

### Detalle de Productos
- `card-header`: `h4` nombre + badge de estado + chips de usos.
- Bajo el encabezado, una fila de **cifras** (`row` con 3 bloques: etiqueta `small.text-muted` + valor `h5`): **Precio de venta** (`money`, «No se vende» si no), **Categoría** («Por revisar» en `badge-outline col-orange`), y con Inventario **Unidad base / Controla stock**.
- Después `dl.row` solo con lo secundario: Descripción (relleno «Sin descripción» atenuado) y, con Inventario, Controla stock; al pie `small.text-muted` «Creado … · Última actualización …».
- Acciones como hoy bajo los datos: Editar (primario), Desactivar (`btn-warning`), Volver (`btn-light`). No se muestran bloques «Hecho con» ni «Se usa en»: aún no existe receta (no mostrar capacidades futuras).

### Formulario de Productos
- Orden: Nombre, Descripción, sección **Usos del producto** (`h5`): Categoría (con ayuda «Organiza y filtra. Materia prima, empaque e intermedio se muestran como Insumo»), interruptor **Se puede vender** y, debajo, Precio de venta (solo si se vende), interruptor **Se puede comprar** con su ayuda inmediatamente bajo el control, y una línea **«Se mostrará como:»** con `app-product-uses` en vivo. Sección Inventario como hoy.
- Corregir la separación entre interruptor y etiqueta (margen inicial) y asociar cada ayuda con `aria-describedby`.

### Servicios (lista, detalle y formulario)
- Lista: importar `table-actions` (los botones hoy salen grises) y usar los mismos iconos `fas` que Productos; buscador con icono como Productos; **Precio** con `money` alineado a la derecha; «Sin especialidad» atenuado; inactivos atenuados. Eliminar el tooltip fijo de cabecera si se reproduce.
- Detalle: misma estructura que el de Productos: `h4` + badge, fila de cifras (**Precio base**, **Duración**, **Especialidad**), `dl` con Código y Descripción, pie con fechas y la etiqueta común «Última actualización».
- Formulario: mismo orden de pie y espaciado; el estado se mantiene como texto informativo.

## Alternativas consideradas
- **Pestañas «Resumen / Receta»** en el detalle: descartado, no hay receta.
- **Menú «⋯» para acciones de fila**: descartado, se aparta de §3 y de todos los módulos; se revisaría en una tarea de sistema.
- **Tabs de rol sobre la lista (Todos · Vendibles · Insumos · Comprables)**: descartado, «Insumo» no es filtrable en el backend sin cambio de API (decisión: sin cambios de backend).
- **Dato nuevo `can_use_in_production`**: descartado por decisión del usuario.

## Comportamiento por privilegio/estado
- Estados de §4: cargando (`loadingIndicator` / «Cargando…»), vacío (mensaje y filtros activos), error de servidor visible con «Reintentar».
- Solo existe rol administrador; el backend sigue siendo la barrera (valida precio obligatorio si se vende, categoría, usos y módulos habilitados). El chip «Insumo» no habilita ni bloquea ninguna operación.

## Consecuencias
- Un patrón compartido nuevo (`app-product-uses`); Inventario conserva su marcado propio como deuda a migrar.
- Se actualiza `design-system.md` §3 (componente) y §5 (lista/detalle de Catálogo).
- Pendiente fuera de alcance: filtro por «Insumo» y bloques «Hecho con / Se usa en» cuando exista Producción.
