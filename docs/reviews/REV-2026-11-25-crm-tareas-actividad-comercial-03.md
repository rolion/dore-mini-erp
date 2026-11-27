# REV-2026-11-25-crm-tareas-actividad-comercial-03: Faltan pruebas de concurrencia, de N+1 y de responsable ajeno en PATCH

**Status:** Resolved (corregido tras el Quality Gate)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-25-crm-tareas-actividad-comercial.md (v1)
**Spec reference:** INV-02, AC-05, AC-06, Edge cases (doble clic en Completar)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
La pruebas de tareas cubren transiciones secuenciales, pero no demuestran el bloqueo de fila (select_for_update) ni la ausencia de N+1; ademas hay una rama sin prueba.

## Expected behavior
Test Specification pide integrar «doble clic en Completar -> un unico cambio»; el cierre de oportunidades ya tiene prueba de concurrencia en este modulo. El listado debe asegurar consultas constantes (describe usa get_many/names por lote). PATCH con owner_id de otra empresa debe responder 400 con prueba.

## Actual behavior
test_filter_by_owner_and_related_without_n_plus_one no usa assertNumQueries (el nombre promete algo que no verifica); no hay prueba con hilos/transacciones concurrentes sobre complete/cancel; no hay prueba de PATCH /tasks/<id>/ con owner_id ajeno (la rama TaskService.edit -> _owner -> 400 no se ejercita).

## Evidence
grep -n 'assertNumQueries\|Thread\|TransactionTestCase' backend/modules/crm/tests/test_api_tasks.py backend/modules/crm/tests/test_domain_task.py -> sin resultados. Las pruebas pasan: 'Ran 139 tests ... OK' (modules.crm).
