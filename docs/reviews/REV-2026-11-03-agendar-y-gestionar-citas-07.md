# REV-2026-11-03-agendar-y-gestionar-citas-07: Huecos de pruebas: ausencias en API y specs de lista/formulario

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-03-agendar-y-gestionar-citas.md (v1)
**Spec reference:** AC-01 (rechazo por ausencia); Test Specification AC-09 (specs de componentes)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
test_create_scheduled_and_rejections cubre turno, pausa y fin fuera de turno pero no una ausencia (Absence); AppointmentListComponent y AppointmentFormComponent no tienen spec (solo detalle y servicio).

## Expected behavior
Prueba de rechazo por ausencia y specs mínimos de lista (filtros/vacío/error) y formulario (conflicto conserva datos, doble envío).

## Actual behavior
La regla de ausencia depende de week_availability (probada en PB-AGE-001), sin prueba de integración en citas; el comportamiento de UI ante 409 en formulario no tiene spec.

## Evidence
ls features/agenda/pages/*.spec.ts -> solo appointment-detail.component.spec.ts. Karma completo: 1129 SUCCESS.
