# REV-2026-11-25-crm-tareas-actividad-comercial-10: TASK desactualizado tras PLAN v3 (REV-04 abierto, conteos de pruebas, versión del plan)

**Status:** Resolved (2026-11-25: TASK actualizado con cifras, PLAN v3 y estado de REV-04)
**Severity:** Low
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-11-25-crm-tareas-actividad-comercial.md (v3)
**Spec reference:** Plan: Changelog / TASK: Review y Plan
**Plan mode:** COMPLETO
**Suggested owner:** delivery-publish

## Description
El TASK conserva afirmaciones anteriores a PLAN v3 y a las últimas correcciones.

## Expected behavior
TASK coherente con PLAN v3 y con los resultados actuales: REV-04 resuelto, versión del plan v3, conteos reales de pruebas, y una fila en el historial de transiciones para la enmienda de INV-03.

## Actual behavior
- Sección «Review»: «Siguen abiertos: REV-04 (INV-03, requiere aprobación...)», pero REV-04 está Resuelto y PLAN v3 lo cierra.
- Sección «Plan»: «(v1, COMPLETO)»; el plan vigente es v3.
- Conteos: TASK declara `modules.crm` 140 pruebas y Karma 1953; hoy son 142 y 1957.
- El historial de transiciones no registra la enmienda v3 / cierre de REV-04.

## Evidence
```
$ manage.py test modules.crm            -> Ran 142 tests ... OK
$ npm test (Karma, ChromeHeadless)      -> TOTAL: 1957 SUCCESS
TASK: "Siguen abiertos: REV-04 (INV-03, requiere aprobación para enmendar la Specification) y REV-08"
TASK: "`docs/plans/PLAN-2026-11-25-crm-tareas-actividad-comercial.md` (v1, COMPLETO)"
REV-04: "**Status:** Resolved (2026-11-25: ...INV-03 enmendada en PLAN v3)"
```
