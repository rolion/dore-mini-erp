# REV-2026-10-30-valorar-recepciones-consumos-costo-historico-01: Rechazo espurio por retroactividad bajo concurrencia (occurred_at se fija antes del bloqueo)

**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-30-valorar-recepciones-consumos-costo-historico.md (v1)
**Spec reference:** INV-05, AC-08, EDGE-04, NFR (atómico y bajo bloqueo)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`RecordMovement.execute` y `RecordOutputs.execute` calculan `occurred_at = timezone.now()` ANTES de tomar el bloqueo del almacén y de la fila de costo. `ValueMovement._check_not_retroactive` rechaza (409 `valuation_blocked`) todo movimiento cuyo `occurred_at` sea menor que el último `occurred_at` valorado del producto.

## Expected behavior
Dos operaciones legítimas y simultáneas sobre el mismo producto (p. ej. una entrega en el almacén A y una recepción en el almacén B) se serializan y ambas se confirman; el rechazo por retroactividad solo debe darse con fechas explícitamente anteriores (AC-08).

## Actual behavior
Si la operación T1 calcula `now()` primero pero T2 obtiene antes el bloqueo de la fila de costo y se guarda con un `occurred_at` mayor, T1 queda con `occurred_at < last` y se rechaza con «No se puede registrar un movimiento con fecha anterior... Use la fecha actual», aunque la persona no eligió ninguna fecha. Falla transitoria, reintentable, pero con un mensaje engañoso en una entrega o recepción.

## Evidence
backend/modules/inventory/application/movement_use_cases.py:49 (`occurred_at=occurred_at or timezone.now()` antes de `with self.repository.locked(warehouse_id)` en la línea 63); backend/modules/costing/application/movement_valuation.py:68-71 (`movement.occurred_at < last`). Para movimientos sin `occurred_at` explícito, la comparación debería usar el instante bajo bloqueo (o tolerar `occurred_at` generado por el sistema). No hay prueba de este escenario (la prueba de concurrencia EDGE-04 no existe).
