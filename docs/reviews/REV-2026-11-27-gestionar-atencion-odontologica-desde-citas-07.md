# REV-2026-11-27-gestionar-atencion-odontologica-desde-citas-07: Especificación y plan desactualizados respecto de lo implementado (API-01, API-07, E2E, AC-12)

**Status:** Open
**Severity:** Low
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-11-27-gestionar-atencion-odontologica-desde-citas.md (v1)
**Spec reference:** API-01, API-07, E2E (Test Specification), AC-12
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
Las desviaciones declaradas son aceptables técnicamente pero la Specification del PLAN no se actualizó:
- **API-07** (sin campo `clinical` en el detalle de Agenda; el frontend consulta `GET /api/dentistry/appointments/<id>/encounter/`): ACEPTABLE y preferible (Agenda no conoce datos clínicos); falta actualizar API-07/UI-08.
- **API-01**: el contrato indica `appointment{…}` anidado; la implementación devuelve ítems planos (`appointment_id`, `customer_name`, …, `encounter_status`, `encounter_id`) y añade `service_name`, `from`, `to`, `next/previous = null`. El frontend es consistente, pero el contrato escrito no coincide.
- **E2E**: Playwright no se instaló. El plan permitía el sustituto (prueba de componente de flujo completo + API de punta a punta) «y se informa», y la instalación requería confirmación; ACEPTABLE condicionado a que el usuario confirme que no exige E2E real (la tarjeta lo menciona en su AC 8). Pendiente de decisión humana.
- **AC-12**: no hay prueba con `MigrationExecutor`; se prueba el estado posterior a la migración (evaluación sin atención conserva `encounter = NULL`). La migración es aditiva y nullable (riesgo bajo), pero el plan pedía «Prueba de migración» explícita; ACEPTABLE con riesgo residual bajo.

## Expected behavior
Specification, Test Specification y mapeo AC↔verificación reflejan la implementación real y las decisiones pendientes.

## Actual behavior
PLAN v1 sin cambios; las desviaciones solo viven en `## Implementación` del TASK.

## Evidence
- `docs/tasks/TASK-gestionar-atencion-odontologica-desde-citas.md` «Desviaciones respecto al plan».
- `backend/modules/dentistry/api/encounter_views.py:106-107` y `application/encounters.py:168-177` (forma plana del listado).
- `backend/modules/dentistry/tests/test_encounter_api.py:306-317` (AC-12).
