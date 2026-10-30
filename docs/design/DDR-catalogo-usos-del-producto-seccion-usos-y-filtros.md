# DDR-catalogo-usos-del-producto-seccion-usos-y-filtros: Sección «Usos del producto» y filtros en Productos

**Estado:** Propuesto
**Task relacionado:** TASK-catalogo-usos-del-producto
**Fecha:** 2026-10-29

## Contexto
El administrador debe poder indicar para cada producto su categoría operativa y si se compra y/o se vende, y encontrar productos por uso, categoría y estado. Los productos existentes quedan «por revisar». Ver `ADR-catalogo-usos-del-producto-modelo-migracion-y-contrato`.

## Pantallas/flujos afectados
1. **Formulario de producto** (alta/edición, `features/products/pages/product-form`).
2. **Lista de productos** (`product-list`).
3. **Detalle** (`product-detail`): filas nuevas de solo lectura.
4. **Selector de productos del pedido** (`sales/components/order-items`): solo ofrece vendibles (sin cambio visual).

## Componentes/patrones elegidos
- Formulario: plantilla «Formulario» + «Sección condicionada por módulo en un formulario» de `design-system.md` (§5). Nueva sección `h5` **«Usos del producto»** antes de «Inventario», con:
  - `select.form-select` **Categoría** (obligatoria, `*`): Materia prima, Empaque, Intermedio, Terminado, Mercadería; con `small.text-muted`: «Organiza y filtra; no limita cómo usas el producto».
  - Dos `form-check form-switch`: **Se puede comprar** y **Se puede vender**, cada uno con ayuda breve («El precio de compra se registra en cada compra»).
  - **Precio de venta** solo visible y obligatorio cuando «Se puede vender» está activo; al apagarlo el campo se oculta sin borrar lo escrito.
  - En edición de un producto sin categoría: `alert alert-warning` «Este producto está por revisar: indica su categoría y si se compra». Guardar exige elegir categoría.
- Lista: plantilla «Lista». Junto al filtro de estado existente se agregan dos `form-select` (**Uso**: Todos / Se compra / Se vende; **Categoría**: Todas / las cinco / Por revisar). Columnas nuevas **Categoría** (texto; «Por revisar» como `badge-outline col-orange` si no tiene) y **Uso** (badges «Compra» / «Venta»; «—» si ninguno); la columna **Precio** muestra «—» si no es vendible.
- Detalle: filas `dt/dd` «Categoría», «Se compra», «Se vende»; «Sin clasificar» si no hay categoría.
- Badges y botones según §3 del sistema de diseño; no se crean componentes nuevos.

## Alternativas consideradas
- **Pestañas** en el formulario: descartado, el formulario es corto y la plantilla usa secciones `h5`.
- **Chips multi-selección para el uso**: descartado, dos interruptores reutilizan el patrón ya existente de «Controlar stock».
- **Banner global de «productos por revisar»**: descartado por esfuerzo; el filtro «Por revisar» y el aviso en edición bastan.

## Comportamiento por privilegio/estado
- Cargando, vacío y error siguen las reglas de §4 existentes; el error de validación del servidor se muestra por campo (`category`, `sale_price`, `can_sell`, `can_buy`).
- Hoy solo existe rol admin. El frontend no es la barrera: el backend rechaza en Ventas productos inactivos o no vendibles y valida categoría y precio al guardar.
- «Controlar stock» y «Unidad base» siguen visibles solo con Inventario habilitado; son independientes de los usos.

## Consecuencias
Deuda visual aceptada: los pedidos que ya contienen un producto que dejó de ser vendible lo siguen mostrando como siempre (snapshot); no se añade indicador. Las pantallas de Compras futuras reutilizarán el mismo patrón de badges.
