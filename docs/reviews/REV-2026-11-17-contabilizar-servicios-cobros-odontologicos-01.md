# REV-2026-11-17-contabilizar-servicios-cobros-odontologicos-01: Pruebas faltantes de rechazos contables, EDGE-04 y N+1

**Status:** Resolved (parcial)
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-17-contabilizar-servicios-cobros-odontologicos.md (v1)
**Spec reference:** AC-09, EDGE-01, EDGE-04
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Faltaban pruebas de `payment_date_not_covered` y `service_date_not_covered`, de prestar tras versionar la proforma y de ausencia de N+1 en el detalle.

## Expected behavior
Cada rama contable y mensaje relevante cubierto y veraz; componentes y estilos coherentes con el sistema de diseño.

## Actual behavior
Ver descripción.

## Evidence
Quality Gate (subagente aislado, 2026-11-17). Resuelto: se añadieron `test_a_service_date_before_the_cutoff_is_rejected_when_the_line_has_advances` y `test_a_payment_date_before_the_cutoff_is_rejected_for_a_recognized_line` (168 pruebas de receivables/quotations/dentistry OK). **Siguen sin prueba EDGE-04 (prestar tras versionar) y el conteo de consultas del detalle** (el repositorio usa un único prefetch): deuda anotada.
