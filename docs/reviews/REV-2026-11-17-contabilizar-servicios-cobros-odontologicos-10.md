# REV-2026-11-17-contabilizar-servicios-cobros-odontologicos-10: Sin prueba de prestar tras versionar (EDGE-04) ni del conteo de consultas del detalle

**Status:** Resolved
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

Resuelto: `test_a_rendered_line_stays_rendered_after_a_new_version` (EDGE-04: sigue prestada, repetir devuelve la misma prestación, el cobro posterior va contra Cuentas por cobrar, un solo reconocimiento) y `test_detail_queries_do_not_grow_with_payments_and_services` (mismo número de consultas con más pagos y prestaciones).
