# REV-2026-10-28-registrar-existencias-iniciales-09: «Movimientos» puede filtrar por un producto que el selector de la lista no ofrece
**Status:** Open (aceptado como limitación conocida; no bloquea)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-27-registrar-existencias-iniciales.md (v2)
**Spec reference:** UI-05, AC-05
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`movement-list.component.ts` (cambio de este task) precarga `productId`/`warehouseId` desde `?product_id=&warehouse_id=` en `filterForm`, pero los `<select>` de producto y almacén se llenan con `productsApi.list({ pageSize: 100 })` y `warehousesApi.list({ pageSize: 100 })`. Si la empresa tiene más de 100 productos y el producto de la fila no está entre los primeros 100, el filtro se aplica a la consulta pero el `<select>` no tiene esa opción: la persona ve una lista filtrada sin ver por qué (solo «Limpiar» lo quita). Limitación heredada de #21 que el nuevo enlace expone.

## Expected behavior
El filtro precargado siempre es visible (p. ej. añadir la opción del producto recibido, o mostrar una etiqueta de filtro activo).

## Actual behavior
Por código: con >100 productos el `<select>` queda sin opción coincidente. Los specs solo comprueban el valor del formulario y la llamada a la API, no el select renderizado.

## Evidence
backend n/a. frontend/panel_admin/src/app/features/inventory/pages/movement-list/movement-list.component.ts:66-73 (patchValue) y :94-99 (carga de opciones con `pageSize: 100`). **No verificado en navegador** (la revisión visual la hace quien orquesta); la severidad es Low por requerir >100 productos.
