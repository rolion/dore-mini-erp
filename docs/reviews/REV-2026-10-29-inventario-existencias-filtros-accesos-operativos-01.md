# REV-2026-10-29-inventario-existencias-filtros-accesos-operativos-01: La preselección del producto falla en silencio si no está entre las primeras 50 opciones

**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-29-inventario-existencias-filtros-accesos-operativos.md (v1)
**Spec reference:** AC-05, UI-03 (EXPECTED 5: «Ambos flujos abren con producto y almacén preseleccionados»)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
«Registrar apertura» y «Registrar ajuste» desde el detalle preseleccionan el producto buscándolo en la lista de opciones que cargan `OpeningProductsService.search(null)` (activos, `tracks_stock`, `page_size=50`). Si el producto del detalle no está entre los 50 primeros por orden, no se preselecciona y la persona debe volver a buscarlo, sin aviso.

## Expected behavior
Con cualquier tamaño de catálogo, al llegar desde el detalle el producto y el almacén de esa existencia aparecen preseleccionados (AC-05).

## Actual behavior
`stock-opening.component.ts` (`watchProducts`): `products.find((p) => p.id === this.preselectedProductId)` sobre las opciones cargadas; sin coincidencia no hace nada. `opening-products.service.ts`: `PRODUCT_OPTIONS_PAGE_SIZE = 50`. La Implementación lo registra como deuda heredada (REV-09 de PB-INV-005), pero el plan no la acepta para este criterio. Con catálogos de más de 50 productos el flujo principal de la historia falla de forma silenciosa.

## Evidence
- Diff `stock-opening.component.ts` líneas del bloque `const match = ...` y `OpeningProductsService` (`page_size` 50).
- Specs solo cubren el caso con el producto dentro de la lista inicial.
- Sugerencia: pedir el producto por id (p. ej. `search` por nombre del producto o `GET /api/products/<id>/`) cuando no esté en las opciones.
