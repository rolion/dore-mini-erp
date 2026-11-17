# REV-2026-11-17-contabilizar-servicios-cobros-odontologicos-10: Sin prueba de prestar tras versionar (EDGE-04) ni del conteo de consultas del detalle

**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-17-contabilizar-servicios-cobros-odontologicos.md (v1)
**Spec reference:** EDGE-04, NFR N+1
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Falta la prueba de que la prestación sigue ligada por `lineage_id` al versionar la proforma y un `assertNumQueries` del detalle.

## Expected behavior
Cobertura de pruebas y documentación coherentes con la Specification y el sistema de diseño.

## Actual behavior
Ver descripción.

## Evidence
Quality Gate, 2.ª pasada (subagente aislado, HEAD b778d3d). Riesgo de regresión financiera no cubierto; pendiente.
