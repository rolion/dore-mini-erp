# DDR-gestionar-recetas-produccion-pantallas-recetas: Menú Producción y pantallas de Recetas

**Estado:** Propuesto
**Task relacionado:** TASK-gestionar-recetas-produccion
**Fecha:** 2026-11-26

## Contexto
Primer uso del menú **Producción**. La persona responsable crea y mantiene recetas (producto resultante, rendimiento e ingredientes). Se reutilizan las plantillas existentes de `docs/design/design-system.md` §5.

## Pantallas/flujos afectados
- Menú lateral: grupo **Producción** (módulo `production`) con el ítem **Recetas** (`/pocketbiz/production/recipes`). «Órdenes de producción» no aparece hasta su tarjeta.
- **Lista** `/production/recipes`: columnas Receta (enlace al detalle), Producto resultante, Rendimiento base (`24 unidad`), Estado, Acciones (ver, editar, activar/desactivar).
- **Alta/Edición** `/production/recipes/new` y `/:id/edit`.
- **Detalle** `/production/recipes/:id`: datos, tabla de ingredientes de solo lectura, acciones. Por debajo de 957 px: datos en filas «etiqueta | valor» y una tarjeta por ingrediente («Producto | nombre», «Cantidad | valor unidad»), sin tabla.

## Componentes/patrones elegidos
- Foco: tras un error de validación el foco va al control del primer error.
- Variante de tarjetas: por debajo de 957 px (`max-width: 956.98px`, igual que Productos y Servicios) la lista pasa a una tarjeta por receta, como `features/services`.
- Lista: plantilla «Lista» (referencia `features/products/pages/product-list`, `features/services`): filtro de estado por defecto **Activos**, buscador, botón «+», tabla Bootstrap con `ngb-pagination` de servidor (patrón de `features/services`, no `ngx-datatable`), badge de estado.
- Formulario: plantilla «Formulario con líneas» de `stock-opening`, **sin** paso de resumen (guardar es reversible; variante de un solo paso del §5): cabecera con Nombre, Producto resultante (`ng-select`), Rendimiento base (número + unidad base del producto, solo lectura); tabla de ingredientes con selector de producto sin repetidos, cantidad, unidad (solo lectura, derivada del producto), quitar y «+ Agregar ingrediente». Pie: Guardar / Cancelar (`unsavedChangesGuard`). Por debajo de 957 px cada línea es una tarjeta («Ingrediente N» con botón quitar, Producto, Cantidad y Unidad de solo lectura) en lugar de una fila de tabla.
- Detalle: plantilla «Detalle» (`dl.row`, badge, fechas `dd/MM/yyyy HH:mm`), acciones Editar (primario), Activar/Desactivar (`btn-warning`, con confirmación al desactivar), Volver.
- Sin componentes nuevos de Oreva. Desviaciones del sistema de diseño aceptadas: tabla Bootstrap con `ngb-pagination` en lugar de `ngx-datatable` (igual que `features/services`) ; la variante de tarjetas ya está implementada (REV-04).

## Alternativas consideradas
- Elegir la unidad por ingrediente en un selector: descartado; sin conversiones solo cabe la unidad base, mostrarla fija evita errores.
- Paso de resumen antes de guardar: descartado, guardar no mueve existencias ni es irreversible.

## Comportamiento por privilegio/estado
- Estados: cargando, vacío («Aún no hay recetas», con CTA «Nueva receta»), error (alerta con reintento), éxito (toast/mensaje y regreso al detalle). Errores de servidor por campo y por línea (`table-warning` + `small.text-danger`) sin borrar lo escrito.
- Receta inactiva: badge «Inactiva», se puede editar y reactivar; no se ofrece a nuevas órdenes.
- Producto de la receta desactivado o con otra unidad base: `alert-warning` en el detalle y en el formulario.
- Módulo `production` deshabilitado: ítem oculto y `moduleGuard` hacia `/module-disabled`. **El backend aplica módulo habilitado, aislamiento por `company_id` y todas las validaciones; el frontend no es la barrera.**
- Responsive: variante compacta de lista (tarjetas bajo 992 px) como en Productos.
- Todo texto vía `translate` con claves es/en/pt idénticas; accesibilidad §7 (labels asociados, foco al primer error).

## Consecuencias
Se añade al §6 del sistema de diseño la entrada «Producción → Recetas». Sin deuda visual nueva; la pantalla de Órdenes reutilizará el selector de receta activa.
