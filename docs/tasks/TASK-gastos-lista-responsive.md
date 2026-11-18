# TASK-gastos-lista-responsive: Lista de Gastos responsive (< 992 px)

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** SI
**Rama:** task/TASK-gastos-lista-responsive (base: `origin/accounting`)
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/101

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-18 | (nuevo) → INVESTIGATION | Task creado (sin tarjeta de Trello; crítica de diseño con la persona) | delivery-start |
| 2026-11-18 | INVESTIGATION → PLANNING | NEEDS_PLAN, diseño SI (DDR escrito) | delivery-start |
| 2026-11-18 | PLANNING → ENGINEERING | Specification READY, PR abierto contra `accounting` | delivery-start |
| 2026-11-18 | ENGINEERING → REVIEW | Implementación y pruebas completas | delivery-build |

## Investigación

### Requerimiento
Hacer responsive la lista de Gastos (`/pocketbiz/expenses`) bajo 992 px (corte `lg`, `CompactViewportService`). Desde 992 px todo igual que hoy. Bajo 992 px: «+» arriba; filtros en panel plegable (botón «Filtros» con contador, `aria-expanded`/`aria-controls`; «Aplicar filtros» consulta, pliega y lleva el foco al resumen); período como `select` primer filtro dentro del panel que precarga Desde/Hasta; total y «Mostrando n–m de N» fuera del panel; tarjetas (1 col, 2 desde 576 px) con `ngb-pagination`; vacío con filtros con badges + «Limpiar filtros» + alta. Sin backend. Decisiones de diseño tomadas con la persona (ver DDR).

### Hechos encontrados
- `expense-list.component.html:33-41` — tres botones de período (`RANGE_SHORTCUTS`, `expense-list.component.ts:29-35`), `aria-pressed` según `currentShortcut`.
- `expense-list.component.ts:116-122` — cada cambio del formulario recalcula `currentShortcut = matchingShortcut()` y consulta (si el rango es válido). Al editar una fecha a mano ningún botón queda activo (`null`), salvo que las fechas coincidan con otro atajo → el `select` debe comportarse igual («Personalizado» = `''`).
- `expense-list.component.ts:127-139` — `applyShortcut` parchea `dateFrom/dateTo` con evento; `clearFilters` deja fechas vacías (= «Todo») y estado `active`.
- `expense-list.component.html:87-148` — `ngx-datatable` de 7 columnas con anchos fijos (suma ≈ 955 px) → se corta en 390 px. Acciones: ver siempre; editar y anular solo si `status === 'ACTIVE'` (`:131-144`).
- `expense-list.component.html:80-85` — total vigente (`data-testid="total"`) del servidor; nota si `showsVoided`.
- `expenses/models/expense.ts:61,122` y `serializers.py:ExpenseSummarySerializer.get_posted` — el resumen de lista ya trae `posted`; no hace falta cambio de API.
- Patrón a reutilizar: `inventory/pages/movement-list` (`compact = inject(CompactViewportService).compact`, `filtersOpen`, `applyAndClose()` con foco al `#summary`, `appliedFilters`/`activeFilterCount`, chips con panel cerrado, `ul.row > li.col-12.col-sm-6 > article.movement-card`, `onPageNumber`, `shownFrom/shownTo`) y `purchases/pages/purchase-list` (botón «+», vacío con filtros con badges). Estilos de tarjeta: `movement-list.component.scss` (`movement-card`, acción 44 px circular). Claves i18n `MOSTRANDO_N_DE_M` existen en INVENTORY, no en EXPENSES.
- `docs/design/design-system.md:161-169` — variante compacta de lista y vacío con filtros.
- No hay Playwright/E2E en `frontend/panel_admin`.

### Hipótesis / supuestos no confirmados
- Ninguna que cambie comportamiento: el «Contabilizado» se decide en el DDR.

### Módulos y dependencias relacionadas
Solo frontend `features/expenses` + `assets/i18n/{es,en,pt}.json` + `design-system.md`. El PR #92 (GAS-02) toca detalle y modelo/servicio de gastos: no se tocan aquí (los archivos de esta tarea son la página de lista, su spec y los i18n).

### Implementaciones similares existentes
Ver Hechos (movement-list, purchase-list, stock-list).

### Comportamiento actual
Ver Hechos. A 390 px la tabla se corta y los filtros ocupan casi una pantalla.

### Restricciones
Sin texto hardcodeado (i18n es/en/pt + `npm run i18n:check`), sin HEX, sin `any`, `ngx-datatable` no se oculta con CSS, Reactive Forms, sin suscripciones colgadas.

### Riesgos identificados
- Conflicto de i18n con otros PR (mismo bloque `EXPENSE_LIST`): bajo, se añaden claves nuevas sin renombrar.
- En compacto el formulario deja de consultar al instante: hay que cubrir que «Aplicar» y «Limpiar» consulten.

### Veredicto de complejidad
**NEEDS_PLAN** — cambio acotado a una pantalla con patrón ya establecido, sin contrato, dominio ni arquitectura nueva.

### Diseño requerido
**SI** — cambia la presentación de una pantalla (filtros, tarjetas, estados vacíos); ver DDR.

## Diseño
`docs/design/DDR-gastos-lista-responsive-lista-compacta.md`

## Arquitectura
No aplica según veredicto.

## Plan
`docs/plans/PLAN-2026-11-18-gastos-lista-responsive.md` (v1, COMPLETO por DDR con impacto visual)

## Implementación
Lista de Gastos con rama compacta (`CompactViewportService` + `@if`) siguiendo `inventory/pages/movement-list` y `purchases/pages/purchase-list`. Sin componentes compartidos nuevos; sin backend.
- AC-01: rama de escritorio intacta (tabla, atajos, aplicación automática); spec «desktop».
- AC-02/03/04/05: «Registrar gasto» arriba, botón «Filtros» con contador/chips/`aria-*`, `select` de período (control `period` fuera de `filterForm`) que precarga fechas sin consultar y vuelve a «Personalizado» al editar; `applyAndClose()` consulta, pliega y enfoca el resumen; `appliedValue` es el snapshot vigente que usan la consulta, el paginado, los chips y el contador.
- AC-06/07: tarjetas `ul > li > article` con acciones de 44 px, `dl` y `ngb-pagination`; vacío con badges/«Limpiar»/alta.
- AC-08: 10 claves nuevas en `EXPENSES.EXPENSE_LIST` (es/en/pt); `i18n:check` 0 faltantes; lint limpio.
- Pruebas: 25 specs del componente (13 nuevos), suite completa 1674 OK.
**Desviaciones:** ninguna. Badge «Anulado» en tarjeta usa `col-grey` (gris, según DDR); la tabla de escritorio conserva rojo. `design-system.md` actualizado con la variante.
**Deuda:** unificar el color del badge Anulado entre tabla y tarjeta si se desea.

## Review
_Pendiente_

## Publicación
_Pendiente_
