# REV-2026-10-30-reportes-adaptar-modulos-activos-01: La prueba test_rejected_module_change_leaves_no_record sigue suponiendo que Reportes requiere Ventas y falla

**Status:** Resolved (corregido en delivery-build, ciclo 2)
**Severity:** High
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-30-reportes-adaptar-modulos-activos.md (v1)
**Spec reference:** AC-11, plan: Integration tests (test_settings_api.py ajustar casos que usaban la dependencia)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-engineer

## Description
`modularity/tests/test_settings_api.py:247-249` (`HistoryTests.test_rejected_module_change_leaves_no_record`) deshabilita `sales` esperando un 409 porque "lo requiere Reportes". Con el cambio de catálogo (Reportes sin `requires`) la operación ahora tiene éxito y deja un registro de historial, por lo que la aserción `count == 0` falla. El plan (Integration tests) pedía ajustar este archivo y el diff no lo toca.

## Expected behavior
Los tests de Modularity reflejan el nuevo catálogo: un cambio rechazado de verdad (p. ej. deshabilitar `expenses` con Compras habilitado, o habilitar un módulo con requisito faltante) no deja registro en el historial.

## Actual behavior
El test falla: `sales/disable` responde 200 y el historial tiene 1 registro.

## Evidence
Ejecución con SQLite en el scratchpad (informativa; el proyecto exige PostgreSQL, no disponible aquí), `manage.py test modules.modularity modules.reporting` (151 tests):
```
FAIL: test_rejected_module_change_leaves_no_record (modules.modularity.tests.test_settings_api.HistoryTests.test_rejected_module_change_leaves_no_record)
  File ".../modules/modularity/tests/test_settings_api.py", line 249, in test_rejected_module_change_leaves_no_record
    self.assertEqual(self.client.get(history_url('modules')).json()['count'], 0)
AssertionError: 1 != 0
```
(La otra falla de esa corrida, `test_concurrency ... database table is locked`, es artefacto de SQLite y no se atribuye al cambio.) Archivo sin cambios en `git diff origin/main...HEAD`.
