# REV-01: El filtro de receta de la lista solo carga las primeras 100 recetas

- **Status:** Open
- **Severity:** Low
- **Category:** IMPLEMENTATION
- **Related plan:** PLAN-2026-11-27-consultar-ordenes-seguimiento-estado (paso 5)
- **Spec reference:** AC-05 (filtros Estado, Receta, Desde y Hasta)
- **Plan mode:** COMPLETO
- **Suggested owner:** delivery-build

## Description
`OrderListComponent.ngOnInit` carga las recetas con `recipesApi.list({ status: 'all', pageSize: 100 })` (maximo permitido por `RecipePagination.max_page_size = 100`) y no pagina.

## Expected
Toda receta de la empresa debe poder elegirse como filtro.

## Actual
Con mas de 100 recetas, las posteriores no aparecen en el selector. Si el error de carga ocurre, el selector queda solo con "Todas las recetas" sin aviso.

## Evidence
`frontend/panel_admin/src/app/features/production/pages/order-list/order-list.component.ts` (ngOnInit, `recipes = page.results`). Riesgo bajo para el volumen actual; aceptable documentarlo como limitacion en el PR.
