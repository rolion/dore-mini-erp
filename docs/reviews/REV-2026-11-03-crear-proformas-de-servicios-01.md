# REV-2026-11-03-crear-proformas-de-servicios-01: La rama está desactualizada respecto a su base y `test_boundaries` falla

**Status:** Resolved (pendiente de re-verificación con PostgreSQL)
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-03-crear-proformas-de-servicios.md (v1)
**Spec reference:** Test Specification, Regression tests («`sales` (límites) siguen verdes»); PLAN Risks («conflictos de fusión con la rama base»)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
La rama `task/TASK-crear-proformas-de-servicios` se creó desde `07d0202`, pero `origin/task/TASK-agendar-y-gestionar-citas` ya avanzó a `2a667e6` («fix(agenda): resolver REV-02 a REV-07 y declarar dependencias de Agenda»). Ese commit declara en `ALLOWED_DEPENDENCIES['agenda']` las fachadas `customers` y `service_catalog`. El TASK registra la falla de `test_boundaries` como «preexistente» y la deja sin tocar, pero ya está corregida en la base.

## Expected behavior
`modules.sales.tests.test_boundaries` pasa en la rama del PR (regresión de límites verde), con la base al día.

## Actual behavior
En la rama tal como está, `test_modules_only_reach_allowed_modules_and_only_through_services` falla. Los infractores son solo de `agenda`; `quotations` no figura. Una fusión de prueba (en un worktree temporal, ya eliminado) con `origin/task/TASK-agendar-y-gestionar-citas` se resuelve sin conflictos y el test pasa.

## Evidence
Rama actual:
```
FAIL: test_modules_only_reach_allowed_modules_and_only_through_services
AssertionError: Lists differ: ['modules\\agenda\\infrastructure\\adapters.py importa modules.customers.services',
 'modules\\agenda\\infrastructure\\adapters.py importa modules.service_catalog.services'] != []
Ran 15 tests ... FAILED (failures=1)
```
Tras `git merge --no-commit --no-ff origin/task/TASK-agendar-y-gestionar-citas` (Auto-merging backend/modules/sales/tests/test_boundaries.py, sin conflictos):
```
Ran 15 tests in 1.035s
OK
```
Corrección sugerida: fusionar o rebasar sobre la base actual, rehacer `makemigrations --check` y actualizar la nota del TASK.
