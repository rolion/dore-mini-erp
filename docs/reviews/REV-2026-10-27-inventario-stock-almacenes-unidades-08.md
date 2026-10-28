# REV-2026-10-27-inventario-stock-almacenes-unidades-08: Proveedores reales de historial y actividad sin enchufar

**Status:** Open
**Severity:** Low
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-10-27-inventario-stock-almacenes-unidades.md (v1)
**Spec reference:** AC-03, AC-09
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
Proveedores reales de historial y actividad sin enchufar.

## Expected behavior
Conectar `shared.stock_history` y `WarehouseActivity` con datos reales.

## Actual behavior
Ningún proveedor registrado; `NoWarehouseActivity` siempre responde no. La siembra del almacén ocurre en un GET.

## Evidence
Revisión de código.

## Resolution
Aceptado y documentado (ADR, TASK); lo cubren las historias de movimientos y recepciones.
