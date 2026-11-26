# REV-2026-11-26-lotes-disponibilidad-inventario-03: Desvíos menores frente a DDR/ADR sin declarar

**Status:** Open
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-26-lotes-disponibilidad-inventario.md (v1)
**Spec reference:** UI-01..UI-02; ADR decisión 5
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
Pequeños desvíos no declarados.

## Expected behavior
Según DDR/ADR.

## Actual behavior
(a) código sin enlace propio, se usa botón «Ver existencia»; (b) sección de lotes de stock-detail pide pageSize 100 y descarta el resto, sin estado de carga propio; (c) el filtro ?product_id= no tiene indicador visible; (d) ADR menciona get_lot_balances, se implementó list_lots_for_product.

## Evidence
Revisión de código del Quality Gate; sin impacto funcional.
