# DDR-gastos-lista-responsive-lista-compacta: Lista de Gastos bajo 992 px

**Estado:** Propuesto
**Task relacionado:** TASK-gastos-lista-responsive
**Fecha:** 2026-11-18

## Contexto
A 390 px la tabla de 7 columnas de `/pocketbiz/expenses` se corta (cabeceras, montos y estado fuera de vista) y los filtros ocupan casi una pantalla antes de ver un gasto. Decisiones tomadas con la persona tras una crítica de diseño.

## Pantallas/flujos afectados
Solo la lista de Gastos. Detalle y formulario no cambian. Desde 992 px (`lg`) nada cambia: tabla `ngx-datatable`, filtros siempre visibles, botones de período y aplicación automática.

## Componentes/patrones elegidos
Plantilla Lista + «Variante compacta de lista» y «Lista de solo lectura con filtros» de `design-system.md` (referencias `stock-list`, `movement-list`, `purchase-list`). Vista elegida con `CompactViewportService` + `@if` (nunca CSS sobre `ngx-datatable`). Sin componente compartido nuevo.

Bajo 992 px, de arriba abajo:
1. **«+ Registrar gasto»** (`btn-primary`, texto visible, ancho completo) antes de los filtros.
2. **Botón «Filtros»** (icono de embudo, contador de filtros aplicados, `aria-expanded`, `aria-controls="expense-filters"`); con el panel cerrado, chips de los filtros aplicados.
3. **Panel plegable**, cerrado al inicio. Orden: **Período** (`select`: Este mes / Mes anterior / Todo / «Personalizado»), Desde, Hasta, Categoría, Estado, «Aplicar filtros» (consulta, pliega y lleva el foco al resumen; un rango invertido mantiene el panel abierto y muestra el error) y «Limpiar filtros» (restablece, consulta y pliega).
   - Elegir un período **precarga** Desde y Hasta, que siguen visibles y editables bajo el `select`. Editar una fecha a mano devuelve el `select` a «Personalizado» (valor neutro `''`), igual que hoy ningún botón queda activo (`currentShortcut = null`); si las fechas editadas coinciden con otro período, el `select` muestra ese (igual que el botón actual). «Personalizado» no es una opción elegible que cambie fechas.
   - El período vive fuera de `filterForm` (control propio) para no entrar en parámetros ni en «Limpiar»; en escritorio se mantienen los tres botones.
4. **Total de gastos vigentes** (con su nota si se ven anulados) y **«Mostrando n–m de N»** (`tabindex="-1"`, destino del foco) fuera del panel.
5. **Tarjetas** (`ul.row > li.col-12.col-sm-6 > article`): cabecera con descripción (enlace al detalle) y fecha debajo, a la izquierda; a la derecha botones circulares de 44 px con las mismas acciones que la tabla (ver siempre; editar y anular solo si el gasto está vigente). Cuerpo `dl`: Categoría («(inactiva)» atenuado si aplica), Método de pago, Proveedor («—» atenuado si falta), **Monto** (derecha, resaltado, `nowrap`, tachado en anulados) y Estado (badge con texto: Vigente `col-green`, Anulado gris — **cambia el rojo actual de la tabla a gris en tarjetas**, como pidió la persona; nunca solo color). Tarjeta de anulado atenuada. `ngb-pagination` (10 por página) bajo las tarjetas; al cambiar de página el foco y el scroll vuelven al resumen.
6. **Vacío con filtros aplicados** (hay chips): mensaje, un badge por filtro aplicado, «Limpiar filtros» y «Registrar gasto». Sin filtros aplicados, solo «No hay gastos que coincidan…» como hoy. El vacío con panel abierto no se muestra duplicado: se renderiza fuera del panel.

### Marca «Contabilizado»: NO se muestra en la lista
`posted` llega en el resumen, pero la tabla actual no lo muestra, ninguna acción de la lista depende de él (editar sigue disponible; la restricción de campos se explica en el detalle, que ya tiene la nota «posted-note»), y una insignia más en una tarjeta de 5 datos compite con el Estado y el Monto. Se mantiene la paridad con la tabla; si la persona necesita verlo en lista, es una tarea aparte para ambos modos.

## Alternativas consideradas
- **Tabla apilada de Bootstrap**: 7 campos por fila ilegibles; descartada (misma justificación que compras).
- **Seguir con los tres botones de período en móvil**: ocupan espacio fijo y duplican los filtros; el `select` dentro del panel ahorra pantalla y mantiene la funcionalidad.
- **Ocultar la tabla con `d-none`**: `ngx-datatable` calcula mal su ancho al reaparecer; se usa `@if`.
- **Aplicar al instante también en móvil**: el panel se cerraría o consultaría al elegir «Desde» antes de «Hasta».

## Comportamiento por privilegio/estado
- Cargando: tarjetas con «Cargando…»; error: toast existente (sin cambio). Vacío: ver punto 6.
- Las acciones editar/anular se muestran según el estado como hoy; el backend es quien impide editar/anular lo no permitido (el frontend no es la barrera).
- Contador y chips reflejan los filtros **aplicados**, no los pendientes de aplicar en el panel.

## Consecuencias
- Deuda: el escritorio conserva badge rojo para anulados y la tarjeta usa gris; se aceptó por decisión de la persona (unificar después si se desea).
- La pantalla pasa a ser consistente con Compras, Existencias y Movimientos. Se actualiza `design-system.md` con una línea para Gastos.
