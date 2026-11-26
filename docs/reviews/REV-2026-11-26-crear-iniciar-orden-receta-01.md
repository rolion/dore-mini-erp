# REV-2026-11-26-crear-iniciar-orden-receta-01: EDGE-01 se prueba solo en secuencia, no con creaciones concurrentes

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-26-crear-iniciar-orden-receta.md (v1)
**Spec reference:** EDGE-01, INV-08
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El plan exige que dos creaciones simultáneas no repitan número (contador bloqueado). La implementación usa `select_for_update().get_or_create` sobre `ProductionOrderCounterModel` dentro de `transaction.atomic`, lo que es correcto por revisión de código, pero la prueba `test_numbers_are_unique_per_company` solo crea órdenes una tras otra y compara con otra empresa.

## Expected behavior
Una prueba (p. ej. `TransactionTestCase` con hilos) o, al menos, un comentario que declare que la garantía descansa en el bloqueo de fila y la restricción única `(company_id, number)`.

## Actual behavior
No hay prueba de concurrencia real; la garantía es solo por diseño.

## Evidence
`backend/modules/production/tests/test_order_api.py::test_numbers_are_unique_per_company`; `order_repository.py::_next_number`. La restricción `production_order_number_unique` protege además a nivel de base.
