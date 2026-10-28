# REV-2026-10-28-inventario-movimientos-trazables-02: Carrera entre registrar movimiento y desactivar almacén / validaciones fuera del bloqueo

**Status:** Resolved (pendiente de re-verificación por delivery-publish)
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-28-inventario-movimientos-trazables.md (v1)
**Spec reference:** INV-05, AC-09, ADR decisión 5
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`RecordMovement.execute` valida `warehouse.active` (y el producto) ANTES de entrar a `repository.locked(warehouse_id)`, y `DeactivateWarehouse.execute` (`application/use_cases.py:84-93`) consulta `has_nonzero_balance` y guarda sin tomar el bloqueo del almacén. Las dos operaciones no están serializadas entre sí.

## Expected behavior
Un almacén con saldo ≠ 0 nunca queda inactivo y no se registran movimientos en un almacén inactivo (AC-09, INV-06), también bajo concurrencia.

## Actual behavior
Entrada concurrente + desactivación: la desactivación lee saldo 0, la entrada pasó la validación `active` y se inserta después, dejando un almacén inactivo con saldo ≠ 0 (o un movimiento en almacén inactivo). El bloqueo `select_for_update` solo protege contra otras escrituras de movimientos.

## Evidence
`backend/modules/inventory/application/movement_use_cases.py:41-47` (validación de almacén fuera del `with self.repository.locked`), `backend/modules/inventory/application/use_cases.py:84-93` (desactivación sin bloqueo), `ConcurrencyTests` (`tests/test_movements.py:229-278`) no cubre este cruce. Severidad Medium: ventana pequeña, aún no hay productores reales. Mitigación: releer `active` bajo el bloqueo y bloquear la fila del almacén en la desactivación.
