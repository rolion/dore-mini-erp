# REV-2026-10-28-inventario-movimientos-trazables-04: Desviaciones menores respecto al DDR/ADR y semántica de reintento tras reversión

**Status:** Resolved (pendiente de re-verificación por delivery-publish)
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-10-28-inventario-movimientos-trazables.md (v1)
**Spec reference:** AC-05, AC-04, INV-03, DDR (filtro producto, columna Origen)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
1) Filtro de producto: `form-select` con solo los primeros 100 productos (declarado en TASK) en lugar de `ng-select` con búsqueda del DDR; con más de 100 productos algunos no se pueden filtrar (AC-05 parcial). 2) La columna «Origen» de la lista muestra solo la etiqueta de clase, no «clase y referencia» como pide el DDR. 3) Un reintento sobre una operación cuyo movimiento ya fue revertido devuelve el movimiento revertido con `created=False` (el contramovimiento no repite el origen), de modo que re-confirmar el documento no vuelve a mover stock y el productor no lo distingue sin mirar `status`; el ADR no define esta política.

## Expected behavior
DDR/ADR actualizados con la desviación aceptada (o implementación conforme) y una política explícita para reintentos tras reversión.

## Actual behavior
Ver arriba; el TASK declara 1 y el contramovimiento sin `source`, pero no actualiza DDR/ADR (estado «Propuesto») ni documenta 2 y 3.

## Evidence
`frontend/.../movement-list.component.ts:95-100` y `.html` (select de productos, pageSize 100; columna Origen línea ~134), `backend/modules/inventory/application/movement_use_cases.py:49-56`, `domain/movement.py` (`reverse`, `source=None`).
