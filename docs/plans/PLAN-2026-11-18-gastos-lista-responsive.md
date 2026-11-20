# PLAN-2026-11-18-gastos-lista-responsive (v1)

**Task:** TASK-gastos-lista-responsive · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-gastos-lista-responsive-lista-compacta / Ninguno

## Objective
Hacer usable la lista de Gastos bajo 992 px (filtros plegables, período como `select`, tarjetas paginadas) sin alterar el escritorio ni el backend.

# Specification
## Current behavior
`expense-list.component.html:33-148` y `.ts:116-139` (ver TASK).

## Expected behavior
Ver DDR (secciones «Componentes/patrones elegidos» y «Marca Contabilizado»).

## Acceptance criteria
- AC-01 ≥ 992 px: tabla, botones de período y filtros visibles con aplicación automática, como hoy.
- AC-02 < 992 px: «Registrar gasto» antes de los filtros; botón «Filtros» con contador y `aria-expanded`/`aria-controls`; panel cerrado al inicio; chips con panel cerrado.
- AC-03 Panel en orden Período, Desde, Hasta, Categoría, Estado, Aplicar, Limpiar. Elegir período precarga Desde/Hasta sin consultar; editar una fecha vuelve el `select` a «Personalizado» (o al período que coincida).
- AC-04 «Aplicar filtros» consulta con los valores del panel, pliega y enfoca el resumen; rango invertido no consulta, deja el panel abierto y muestra el error. «Limpiar filtros» restablece y consulta.
- AC-05 Total vigente y «Mostrando n–m de N» fuera del panel.
- AC-06 Tarjetas en vez de tabla (sin `ngx-datatable` en el DOM), `ngb-pagination`, cabecera con descripción/fecha y acciones de 44 px (ver siempre; editar/anular solo vigentes), `dl` con Categoría, Método, Proveedor («—»), Monto y Estado con texto; anulados atenuados.
- AC-07 Vacío con filtros aplicados: badges, «Limpiar filtros» y alta; sin filtros: mensaje simple.
- AC-08 Textos solo vía claves i18n es/en/pt (`npm run i18n:check`), sin HEX ni `any`.

## Edge cases / Error cases
Rango invertido; categoría inactiva («(inactiva)»); proveedor vacío; anulados visibles (nota «no se suman»); cambio de ancho de pantalla con el panel abierto (se usa `@if`, el estado de `filtersOpen` se conserva); error de carga (toast, sin cambios).

## Out of scope
Backend/API, detalle, formulario, marca «Contabilizado» (decidido NO en el DDR), color del badge de escritorio, PR #92.

# Test Specification
## Unit tests (specs del componente, `CompactViewportService` sustituido por un stub con señal)
Modo escritorio: AC-01 (tabla + atajos, parámetros iniciales y atajos existentes siguen verdes). Modo compacto: AC-02, AC-03 (precarga sin consulta; edición manual → «Personalizado»), contador/chips, AC-04 (aplicar consulta y pliega; foco; rango inválido), AC-05, AC-06 (tarjetas, acciones por estado, «—», paginación), AC-07 (vacío con y sin filtros).
## E2E: NO
No hay infraestructura E2E en el proyecto y instalar Playwright exige dependencia nueva; el comportamiento es de presentación sobre una API ya probada. La verificación visual a 390/576/992 px se hace con el navegador integrado en `delivery-publish`.
## Acceptance criteria mapping
| AC | Verificación |
|---|---|
| AC-01..07 | Specs del componente (arriba) |
| AC-08 | `npm run i18n:check`, prueba de paridad de claves, `npm run lint`, revisión del diff |

# Implementation Plan
## Proposed solution
Seguir `movement-list`: `compact`, `filtersOpen`, `applyAndClose()`, `appliedFilters` (snapshot de lo aplicado), `viewChild('summary')`. En compacto, `valueChanges` solo recalcula el período y el rango (no consulta). Control `period` aparte de `filterForm`.
## Files/components affected
- `frontend/panel_admin/src/app/features/expenses/pages/expense-list/expense-list.component.{ts,html,scss,spec.ts}`
- `frontend/panel_admin/src/assets/i18n/{es,en,pt}.json` (claves nuevas en `EXPENSES.EXPENSE_LIST`)
- `docs/design/design-system.md` (una línea de variante)
## Implementation steps
1. `npm ci`; ts: `compact`, `filtersOpen`, `period`, snapshot aplicado, `applyAndClose`, `appliedFilters`, `shownFrom/To`, `onCardsPage`, valueChanges condicionado (AC-02..05).
2. html: rama compacta (+ arriba, toolbar, panel, resumen, tarjetas, vacío) y rama escritorio intacta (AC-01, 06, 07).
3. scss de tarjetas (tokens Bootstrap, sin HEX) (AC-06).
4. i18n es/en/pt (AC-08).
5. Specs de ambos modos; `npm test`, `lint`, `i18n:check`, build.
6. Actualizar `design-system.md`.
## Database / migrations
No aplica.
## Risks
Estado del badge «Anulado» gris: confirmar clase gris existente (`col-grey`/`bg-secondary`) al implementar.
## New dependencies
Ninguna (`npm ci` ya autorizado).
