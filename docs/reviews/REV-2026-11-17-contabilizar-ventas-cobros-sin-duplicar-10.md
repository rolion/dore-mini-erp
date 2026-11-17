# REV-2026-11-17-contabilizar-ventas-cobros-sin-duplicar-10: Falta probar la falla del asiento al entregar con salida de almacén

**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-17-contabilizar-ventas-cobros-sin-duplicar.md (v3)
**Spec reference:** AC-14 / INV-06
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
No hay prueba que combine Inventario y Contabilidad: una falla del asiento en la entrega no debe dejar salida de almacén.

## Expected behavior
Prueba de integración con Inventario habilitado y un faltante contable.

## Actual behavior
La garantía es estructural (`transaction.atomic()` en `_run`) sin aserción.

## Evidence
`test_sales_posting.py` sin referencias a inventario; `test_delivery_inventory.py` sin Contabilidad. Hallado por el Quality Gate v3 (subagente aislado, 2026-11-17).
