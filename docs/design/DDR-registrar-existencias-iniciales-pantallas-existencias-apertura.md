# DDR-registrar-existencias-iniciales-pantallas-existencias-apertura: Existencias y formulario de apertura

**Estado:** Propuesto
**Task relacionado:** TASK-registrar-existencias-iniciales
**Fecha:** 2026-10-27

## Contexto
La historia pide un formulario de apertura accesible desde Inventario → Existencias → «Registrar apertura», con revisión antes de confirmar. «Existencias» aún no existe: se crea una pantalla mínima (saldos por almacén y movimientos de un producto+almacén) que sirve de punto de entrada y de destino tras confirmar.

## Pantallas/flujos afectados
1. **Existencias** (`/pocketbiz/inventory/stock`): lista de saldos con filtro de almacén; botón «Registrar apertura».
2. **Registrar apertura** (`/pocketbiz/inventory/stock/opening`): formulario en dos pasos dentro de la misma ruta (Editar → Resumen).
3. **Movimientos** (`/pocketbiz/inventory/stock/movements?product_id=&warehouse_id=`): historial de un producto en un almacén.
4. Submenú Inventario: se agrega «Existencias» (el formulario de apertura **no** tiene entrada de menú propia).

## Componentes/patrones elegidos
- **Existencias — plantilla Lista** (`features/products/pages/product-list`, tabla Bootstrap apilada como `inventory/components/_inventory-table.scss`). Columnas: Producto, Almacén, Existencia (con abreviatura de unidad), Acciones (enlace «Movimientos»). Filtro: selector de almacén (por defecto, el predeterminado; opción «Todos»). Botón primario «Registrar apertura» en la cabecera. Paginación externa. Vacío: «Aún no hay existencias registradas. Usa «Registrar apertura» para cargar el stock inicial.»
- **Apertura — plantilla Formulario** (`product-form`) con la parte de líneas siguiendo `features/sales/pages/order-form`:
  - Cabecera: Almacén (`form-select`, solo activos, predeterminado preseleccionado), Fecha (`input type=date`, por defecto hoy, máximo hoy), Referencia (texto, obligatorio, p. ej. «Inventario inicial octubre»).
  - Líneas (tabla): Producto (selector con búsqueda, solo productos activos que controlan stock; los ya elegidos aparecen deshabilitados para impedir duplicados), Unidad base (solo lectura, texto), Cantidad inicial (numérica ≥ 0; sin decimales si la unidad no admite fracciones, hasta 3 si las admite), botón quitar. «+ Agregar línea» bajo la tabla. Una línea nueva vacía al abrir.
  - Línea con movimientos previos: al elegir producto o cambiar almacén se consulta el historial; la fila se marca con `table-warning`, un `alert alert-warning` encima de la tabla lista cuáles y por qué («Ya tiene movimientos en este almacén; corrige con un ajuste.») y se bloquea «Revisar resumen» hasta quitarla. El mismo mensaje se muestra si el servidor responde 409.
  - Pie: «Revisar resumen» (primario) y «Cancelar» (`btn-light ms-2`, vuelve a Existencias sin crear nada; con cambios sin guardar aplica `unsavedChangesGuard`).
- **Resumen (segundo paso, misma ruta):** `card` con `dl.row` (Almacén, Fecha, Referencia, Total de productos) y tabla Producto / Cantidad + unidad. Botones: «Confirmar apertura» (primario), «Volver a editar» (`btn-light`). «Confirmar» se deshabilita y muestra «Registrando…» mientras la petición está en curso; la clave de idempotencia se genera al abrir el formulario y se reutiliza en cada reintento. Aviso: «Esta carga no se puede editar después; las correcciones se hacen con ajustes.»
- **Éxito:** navega a Existencias filtrada por el almacén, con `ToastrService` «Apertura registrada» y las filas nuevas visibles con su enlace «Movimientos». Si la respuesta es una réplica (200), se muestra el mismo resultado sin avisar de error.
- **Movimientos — plantilla Lista simplificada:** cabecera con producto, almacén y existencia actual; tabla Fecha, Tipo («Apertura»), Cantidad, Referencia, Registrado por/fecha; botón «Volver a existencias».
- Nuevo patrón reutilizable (se agrega a `docs/design/design-system.md`): **Formulario con líneas y paso de resumen** (editar → resumen → confirmar con envío único).

## Alternativas consideradas
- **Asistente en pasos con rutas distintas:** más navegación y pérdida de estado; se prefiere un solo componente con dos vistas (menos esfuerzo, mantiene el borrador).
- **Diálogo modal para la apertura:** inadecuado para tablas de varias líneas en móvil.
- **Importación masiva (CSV):** fuera de la historia.
- **Entrada de menú propia para la apertura:** descartada por el requerimiento.

## Comportamiento por privilegio/estado
- Estados: cargando (indicador en tabla y selectores), vacío (mensajes arriba), error de validación (`small.text-danger` por campo y por línea), error de servidor (alerta visible, el borrador se conserva), éxito (toast + navegación).
- Con el módulo Inventario deshabilitado, las rutas redirigen por `moduleGuard` y el submenú no aparece.
- El frontend **no es la barrera**: el backend aplica módulo habilitado, rol administrador, empresa del usuario, producto que controla stock, cantidades y duplicados; un 403 se muestra como mensaje.

## Consecuencias
- Deuda aceptada: la pantalla de Existencias es mínima (sin búsqueda por nombre ni kardex completo); el menú ya tiene «Inicio» como placeholder.
- Se añade un patrón nuevo al sistema de diseño; `order-form` y la apertura comparten tabla de líneas pero no componente (extraerlo se evalúa cuando exista una tercera pantalla con líneas).
