# REV-2026-10-27-inventario-stock-almacenes-unidades-04: Carrera de make-default se reportaba como nombre duplicado

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-27-inventario-stock-almacenes-unidades.md (v1)
**Spec reference:** INV-06
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Carrera de make-default se reportaba como nombre duplicado.

## Expected behavior
Mensaje acorde a la causa.

## Actual behavior
Todo IntegrityError se traducía a «Ya existe un almacén con ese nombre» (400).

## Evidence
Revisión de `DjangoWarehouseRepository.save`.

## Resolution
Ahora distingue: nombre duplicado → 400; otro caso → 409 `warehouse_default_changed`.
