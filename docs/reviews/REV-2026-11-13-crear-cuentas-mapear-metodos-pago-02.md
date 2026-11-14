# REV-2026-11-13-crear-cuentas-mapear-metodos-pago-02: Sin test de concurrencia (EDGE-06) ni de carrera desactivar vs. asignar

**Status:** Resolved
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-13-crear-cuentas-mapear-metodos-pago.md (v1)
**Spec reference:** EDGE-06
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El `PUT` de método usa único + `update_or_create` y `lock_company` con `select_for_update`, pero `test_api.py` no los prueba.

## Expected behavior
Un test de concurrencia (patrón de `modularity/tests/test_concurrency.py`).

## Actual behavior
Ver descripción.

## Evidence
Implementación en `repositories.py:73-79`; sin test asociado.

## Resolution (2026-11-13)
`accounting/tests/test_concurrency.py`: `PUT` simultáneo y carrera desactivar vs. asignar.
