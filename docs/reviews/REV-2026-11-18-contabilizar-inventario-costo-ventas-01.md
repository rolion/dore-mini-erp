# REV-2026-11-18-contabilizar-inventario-costo-ventas-01: Posible deadlock entre el bloqueo por almacén y el de la empresa

**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-17-contabilizar-inventario-costo-ventas.md (v1)
**Spec reference:** INV-03 / ADR (serializado por lock_company_stock)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
record_movement y record_outputs bloquean primero el almacén hasta el fin de la transacción; después cost_receipt/cost_outputs piden lock_company_stock (todos los almacenes de la empresa).

## Expected behavior
Un orden de bloqueo consistente: tomar el bloqueo de la empresa antes de registrar movimientos, o bloquear solo lo necesario.

## Actual behavior
Dos entregas o recepciones concurrentes de la misma empresa en almacenes distintos pueden esperarse mutuamente; PostgreSQL abortaría una con 'deadlock detected' (500). Sin corrupción de datos.

## Evidence
Análisis de código (Quality Gate): inventory/infrastructure/django/movement_repository.py:96-109 y costing/application/cost_use_cases.py. No reproducido con hilos.
