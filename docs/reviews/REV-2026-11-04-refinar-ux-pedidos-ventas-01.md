# REV-2026-11-04-refinar-ux-pedidos-ventas-01: «Más filtros» tiene aria-controls hacia un id que no existe mientras está cerrado

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-04-refinar-ux-pedidos-ventas.md (v1)
**Spec reference:** AC-09 (`aria-expanded`); docs/design/design-system.md sección 8 (accesibilidad)
**Plan mode:** COMPACTO
**Suggested owner:** frontend (features/sales)

## Description
El botón `data-testid="more-filters"` declara `aria-controls="more-filters"`, pero el panel `#more-filters` solo se renderiza dentro de `@if (moreFiltersOpen)`.

## Expected behavior
Con el panel colapsado, `aria-controls` no debe apuntar a un id inexistente: o el panel siempre está en el DOM (`[hidden]`/clase `collapse`) o se omite `aria-controls` mientras está cerrado.

## Actual behavior
Con `moreFiltersOpen = false` el atributo referencia un elemento ausente. `aria-expanded` sí es correcto. Impacto leve en lectores de pantalla.

## Evidence
frontend/panel_admin/src/app/features/sales/pages/order-list/order-list.component.html: botón con `aria-controls="more-filters"` y `@if (moreFiltersOpen) { <div id="more-filters" ...>`.
