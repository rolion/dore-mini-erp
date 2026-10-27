# DDR-inventario-stock-almacenes-unidades-pantallas-inventario: Sección «Inventario» del producto y Configuración de Inventario

**Estado:** Propuesto
**Task relacionado:** TASK-inventario-stock-almacenes-unidades
**Fecha:** 2026-10-27

## Contexto
El administrador marca qué productos controlan existencias y define las unidades y los almacenes que usarán. Los datos de inventario solo se ven cuando el módulo Inventario está habilitado; un producto sin control de stock sigue funcionando como hasta ahora.

## Pantallas/flujos afectados
1. **Formulario de producto** (`/catalog/products/new`, `/:id/edit`): nueva sección «Inventario».
2. **Listado de producto** (`/catalog/products`): columnas «Controla stock» y «Unidad base».
3. **Detalle de producto**: filas «Controla stock» y «Unidad base».
4. **Inventario → Almacenes y unidades** (nueva, `/inventory/configuration`): pestañas «Almacenes» y «Unidades».
5. **Menú Inventario**: el submenú pasa a «Inicio», «Almacenes y unidades» y «Ajustes» (la pantalla de ajustes de PB-CFG-001 en `/inventory/settings` se mantiene tal cual).

## Componentes/patrones elegidos
- **Formulario de producto** (design-system §5 Formulario, referencia `product-form`): debajo de Precio, un bloque `<h5>` «Inventario» solo si `ModulesService` indica Inventario habilitado. Contiene un interruptor `form-check form-switch` «Controlar stock» (desactivado por defecto) y, solo cuando está activo, un `form-select` «Unidad base» (obligatorio, marcado con `*`) con las unidades activas, más la unidad actual aunque esté inactiva. Si no hay unidades activas: `small.text-muted` «Primero crea una unidad en Inventario › Almacenes y unidades» con enlace. Con Inventario deshabilitado el bloque no aparece y el formulario no envía esos campos. Errores del servidor por campo (`small.text-danger`).
- **Bloqueo por historial:** si el servidor responde 409 `stock_history_locked`, `alert alert-warning` sobre el pie del formulario: «Este producto tiene movimientos de inventario; no se puede cambiar el control de stock ni la unidad base. Usa el procedimiento de regularización.»; los demás datos conservados no se pierden.
- **Lista** (design-system §5 Lista): dos columnas nuevas («Controla stock» con badge `col-green` «Sí» / `col-grey` «No» y «Unidad base» con abreviatura) que solo se renderizan con Inventario habilitado. Sin costo ni valor de inventario.
- **Detalle:** `dt/dd` «Controla stock» (Sí/No) y «Unidad base» («Sin unidad» cuando corresponde), solo con Inventario habilitado.
- **Almacenes y unidades** (design-system §5 Formulario de configuración con pestañas, referencia `module-settings`; tabla de la plantilla Lista): `.card` con `h4` «Inventario › Almacenes y unidades» y `nav-tabs` (`role="tablist"`) «Almacenes» / «Unidades». Cada pestaña: buscador por nombre, filtro de estado (por defecto **Activos**), botón «+» y tabla Bootstrap simple apilada en móvil (como `category-list`; no `ngx-datatable`, que es excesivo para pocas filas). El alta/edición abre un diálogo modal (patrón `category-dialog` de gastos) con Reactive Forms.
  - Almacenes: columnas Nombre, Descripción, Estado (badge), «Predeterminado» (badge «Predeterminado» en el vigente); acciones Editar, «Definir predeterminado» (solo activos no predeterminados), Activar/Desactivar. El diálogo incluye nombre (`*`), descripción y casilla «Predeterminado».
  - Unidades: columnas Nombre, Abreviatura, «Admite fracciones» (Sí/No), Estado; acciones Editar y Activar/Desactivar. Con la unidad en uso, el diálogo muestra nombre, abreviatura y fracciones **deshabilitados** con `small.text-muted` «Esta unidad ya está asignada a productos; solo se puede activar o desactivar.»
  - No hay botón de eliminar.
- **Motivos de bloqueo:** al desactivar un almacén con saldo, recepción pendiente o siendo el predeterminado, el 409 se muestra en un `alert alert-warning` sobre la tabla con el `detail` del servidor; el estado no cambia.
- Estados (design-system §4): cargando (`loadingIndicator`/«Cargando…»), vacío («Sin almacenes.» / «Sin unidades. Crea la primera con +.»), error de validación por campo, error de servidor visible, éxito con toast.

## Alternativas consideradas
- **Poner «Almacenes y unidades» como pestañas dentro de `/inventory/settings`:** la pantalla actual es genérica (`ModuleSettingsComponent`: General/Historial). Mezclarlas obligaría a incrustar ese componente en otro. Se prefiere una ruta propia y se conserva «Ajustes». Desviación del texto «Inventario → Configuración»: el submenú dice «Almacenes y unidades» (reversible renombrando entradas de menú).
- **Formulario en página completa en lugar de diálogo:** más rutas para dos campos; descartado por consistencia con categorías de gastos.
- **Mostrar los campos de inventario siempre:** contradice «solo con Inventario habilitado».

## Comportamiento por privilegio/estado
- Solo el administrador de la empresa opera estas pantallas; el backend responde 403 a otros y 403 si Inventario está deshabilitado en la API de unidades/almacenes. El frontend (ocultar columnas, deshabilitar controles) no es la barrera de seguridad: el servidor valida que la unidad sea activa y de la empresa, el bloqueo por historial, la obligatoriedad de la unidad y el almacén predeterminado.
- Unidades y almacenes inactivos siguen visibles con el filtro «Inactivos»/«Todos»; no se ofrecen para nuevas asignaciones.

## Consecuencias
Se actualiza `docs/design/design-system.md` (§5: sección de producto con interruptor/selector, lista con pestañas y diálogo; §6: submenú de Inventario). Deuda: nombre de menú distinto del literal «Configuración»; tabla simple sin ordenamiento; sin pantalla de regularización (el mensaje solo la menciona).
