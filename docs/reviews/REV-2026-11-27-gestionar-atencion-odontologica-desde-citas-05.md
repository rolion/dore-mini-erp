# REV-2026-11-27-gestionar-atencion-odontologica-desde-citas-05: Con Agenda o Personal deshabilitados la ficha del paciente muestra un error permanente en «Atenciones»

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-27-gestionar-atencion-odontologica-desde-citas.md (v1)
**Spec reference:** AC-07 (módulos deshabilitados), UI-07, required_modules de los endpoints
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Los endpoints de atención exigen `('dentistry','agenda','customers','personnel')`, pero el módulo `dentistry` solo declara `requires=('customers',)`. La ficha del paciente monta siempre `<app-patient-encounters>` y el submenú «Citas» aparece con solo `dentistry`.

## Expected behavior
Una empresa con Odontología pero sin Agenda/Personal (posible desde Ajustes) no debería ver un error en cada ficha ni un submenú que lleva a pantallas con error; o bien se declara la dependencia, o el frontend oculta la tarjeta/submenú sin esos módulos.

## Actual behavior
`GET /api/dentistry/patients/<id>/encounters/` responde 403 `module_disabled` y la tarjeta muestra `alert-danger` en toda ficha (mensaje «sin permiso o módulo no habilitado»). El listado «Citas» también falla. La prueba `test_module_disabled_blocks_endpoints` valida el 403, no la experiencia en el frontend.

## Evidence
- `backend/modules/modularity/domain/modules.py:27` (`dentistry` requiere solo `customers`).
- `backend/modules/dentistry/api/encounter_views.py:74-75` (`required_modules`).
- `frontend/panel_admin/src/app/features/dentistry/components/patient-encounters.component.ts` (sin comprobar módulos) y `pages/patient-detail.component.html` (siempre incluida).
