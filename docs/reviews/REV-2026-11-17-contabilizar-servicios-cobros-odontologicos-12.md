# REV-2026-11-17-contabilizar-servicios-cobros-odontologicos-12: PLAN v1 no recoge el código `service_date_not_covered`

**Status:** Resolved
**Severity:** Low
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-11-17-contabilizar-servicios-cobros-odontologicos.md (v1)
**Spec reference:** AC-09, EDGE-01
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
AC-09/EDGE-01 decían `payment_date_not_covered`/`fiscal_period_unavailable` para la fecha de prestación sin cobertura con anticipos.

## Expected behavior
Cobertura de pruebas y documentación coherentes con la Specification y el sistema de diseño.

## Actual behavior
Ver descripción.

## Evidence
Quality Gate, 2.ª pasada (subagente aislado, HEAD b778d3d). PLAN anotado (v1.1, solo Implementation Plan): el código es `service_date_not_covered`; sin cambio de comportamiento ni de Specification.
