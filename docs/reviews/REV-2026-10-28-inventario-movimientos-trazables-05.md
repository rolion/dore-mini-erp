# REV-2026-10-28-inventario-movimientos-trazables-05: La corrección de REV-02 no tiene prueba de concurrencia (registrar vs. desactivar almacén)

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-28-inventario-movimientos-trazables.md (v1)
**Spec reference:** INV-05, AC-09, ADR decisión 5
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
La corrección de REV-02 (validar `active` bajo `repository.locked` en `RecordMovement` y tomar el mismo bloqueo de fila del almacén en `DeactivateWarehouse`) es correcta por lectura de código, pero ninguna prueba la fija: se puede quitar el `with self.repository.locked(...)` de `DeactivateWarehouse.execute` y toda la suite sigue en verde.

## Expected behavior
Una prueba `TransactionTestCase` que ejecute en paralelo una entrada y una desactivación del mismo almacén (con saldo 0 al inicio) y afirme el invariante: o bien el almacén queda inactivo y la entrada falla con «almacén inactivo», o bien la entrada se registra y la desactivación falla con `warehouse_has_stock`; nunca inactivo con saldo distinto de cero.

## Actual behavior
Solo hay pruebas secuenciales (`test_warehouse_with_balance_cannot_be_deactivated`, `DeactivateWithActivityTests` con actividad falsa). `ConcurrencyTests` cubre salidas simultáneas y reversiones simultáneas, no este cruce.

## Evidence
`backend/modules/inventory/tests/test_movements.py` (sin test que combine `inventory.record_movement` y `DeactivateWarehouse` en hilos); `backend/modules/inventory/tests/test_warehouses.py` (desactivación con `FakeActivity`, sin bloqueo real). Revisión de código: ambos caminos bloquean la misma fila (`WarehouseModel` filtrada por empresa) antes de leer saldo/estado y sin otros bloqueos, por lo que no hay carrera ni riesgo de deadlock; el hueco es solo de cobertura.
