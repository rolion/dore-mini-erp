# REV-2026-11-17-contabilizar-servicios-cobros-odontologicos-08: Sin prueba del texto nuevo del mensaje de rectificación

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-17-contabilizar-servicios-cobros-odontologicos.md (v1)
**Spec reference:** INV-07, AC-11
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Ningún test del backend afirma «La línea tiene cobros o ya fue prestada: no se puede rectificar.» en quotations ni dentistry.

## Expected behavior
Cobertura de pruebas y documentación coherentes con la Specification y el sistema de diseño.

## Actual behavior
Ver descripción.

## Evidence
Quality Gate, 2.ª pasada (subagente aislado, HEAD b778d3d). Pendiente.

Resuelto: `test_a_rendered_line_cannot_be_rejected...` (cotizaciones) y `test_a_rendered_dental_line_cannot_be_rejected_and_says_why` (Odontología) afirman el texto «ya fue prestada».
