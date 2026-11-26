# REV-2026-11-25-crm-tareas-actividad-comercial-09: Sin prueba de que archivar una tarea hecha conserva completed_at (INV-03 v3)

**Status:** Resolved (2026-11-25: pruebas de dominio y API añadidas; modules.crm 145 OK)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-25-crm-tareas-actividad-comercial.md (v3)
**Spec reference:** INV-03, AC-04
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
PLAN v3 enmendó INV-03: al archivar una tarea hecha, `completed_at` se conserva; la restricción `crm_task_completed_coherent` ya permite `archived` con o sin fecha. Ninguna prueba ejercita esa rama.

## Expected behavior
Una prueba de dominio y/o API que complete una tarea, la archive y compruebe `status == archived` con `completed_at` intacto (y que archivada desde cancelada lo tiene nulo).

## Actual behavior
`test_transitions`, `test_invalid_transitions` (dominio) y `test_cancel_reopen_archive` (API) solo archivan desde `cancelled`; ninguna archiva desde `done`. Un cambio que borre `completed_at` en `archive()` no rompería ninguna prueba.

## Evidence
```
$ grep -n "archive" backend/modules/crm/tests/test_domain_task.py
54:        task.archive()      # tras task.cancel()
59:        for action in (task.reopen, task.archive):  # una pendiente...
63:        task.archive()      # tras task.cancel()
$ test_api_tasks.py::test_cancel_reopen_archive: ... self.act(task['id'], 'cancel'); archive  (nunca done -> archive)
```
Suite `modules.crm`: 142 pruebas OK (no detecta la ausencia).
