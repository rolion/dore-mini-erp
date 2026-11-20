# TASK-productos-tabla-desde-957px: Productos en tarjetas solo bajo 957 px; tabla desde 957 px

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** NO
**Rama:** task/TASK-productos-tabla-desde-957px
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/112

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-20 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-11-20 | INVESTIGATION → PLANNING | Veredicto NEEDS_PLAN, sin diseño nuevo | delivery-start |
| 2026-11-20 | PLANNING → ENGINEERING | Plan v1 READY | delivery-start |

## Investigación

### Requerimiento
«Los productos como card solo deberían mostrarse de esta forma cuando la pantalla tiene un ancho menor a 957 px; cuando es mayor a 957 px se muestra la tabla normal.» Captura: en escritorio (~1900 px) hoy se ven tarjetas en rejilla de 4 columnas.

### Hechos encontrados
- `frontend/panel_admin/src/app/features/products/pages/product-list/product-list.component.html:89-149` — la lista renderiza SIEMPRE `ul.product-cards` > `li.product-card`; no hay tabla.
- `product-list.component.ts:19` — `COMPACT_QUERY = '(max-width: 991.98px)'`; `compact` (`:45`, `:96-99`) hoy solo controla los filtros colapsables (`html:26,41,76`) y `applyOnDesktop` (`ts:185`).
- Commit `18f8cfff` reemplazó el `ngx-datatable` por tarjetas para todos los anchos (columnas previas: Nombre, Categoría, Usos, Precio, Estado, Unidad base si Inventario activo, acciones).
- Patrón a seguir: `features/inventory/pages/stock-list/stock-list.component.html:128-206` — `@if (compact) { tarjetas } @else { div.table-responsive > table.table }` con `ng-template` compartidos; `docs/design/design-system.md:162-171` (variante compacta de lista, bajo 992 px).
- `product-list.component.scss:1` define `$compact-max: 991.98px` y los estilos de tarjeta; `product-list.component.spec.ts:42` fuerza escritorio con un `BreakpointObserver` simulado y `:127-137` espera tarjetas en escritorio.

### Hipótesis / supuestos no confirmados
- 957 px es el corte solicitado y sustituye a 992 px para esta pantalla: «menor a 957» = `max-width: 956.98px`; con 957 px exactos se ve la tabla.
- Los filtros colapsables (hoy ligados a `compact`) se mueven al mismo corte para no tener, entre 957 y 991 px, tabla con filtros plegados.

### Módulos y dependencias relacionadas
Solo frontend, feature `products`. Sin backend, API ni migraciones.

### Implementaciones similares existentes
`stock-list`, `purchase-list`, `expense-list`, `customer-list` (todas tabla en escritorio y tarjetas en compacto, corte 992).

### Comportamiento actual
Tarjetas en todos los anchos; filtros colapsan bajo 992 px.

### Restricciones
Sin texto hardcodeado (`translate`, claves en es/en/pt); sin `any`; acciones de 44 px en tarjetas; `COMMON.*` ya existe para las cabeceras (`NOMBRE`, `ESTADO`, `ACCIONES`).

### Riesgos identificados
- Entre 957 y 991 px los campos de filtro usan `col-lg-*` (≥ 992) y se apilan en 2 columnas (`col-md-6`): aceptable.
- Desviación respecto del corte 992 px del sistema de diseño; se documenta en `design-system.md`.

### Veredicto de complejidad
**NEEDS_PLAN** — Cambio acotado a un componente, sin lógica de negocio ni contrato; requiere restaurar una vista de tabla y ajustar pruebas.

### Diseño requerido
**NO** — Reutiliza la plantilla de lista del sistema de diseño (tabla en escritorio, tarjetas en compacto); solo cambia el corte.

## Diseño
No aplica.

## Arquitectura
No aplica según veredicto.

## Plan
docs/plans/PLAN-2026-11-20-productos-tabla-desde-957px.md (v1, COMPACTO, READY)

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
