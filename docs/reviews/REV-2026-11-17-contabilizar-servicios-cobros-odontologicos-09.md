# REV-2026-11-17-contabilizar-servicios-cobros-odontologicos-09: Sin prueba del permiso clínico sobre `services/`

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-17-contabilizar-servicios-cobros-odontologicos.md (v1)
**Spec reference:** AC-12
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
No hay prueba de que `POST /api/receivables/commitments/dental/<n>/services/` exija acceso clínico (403 sin él). El código reutiliza `_authorize`, probado para el detalle.

## Expected behavior
Cobertura de pruebas y documentación coherentes con la Specification y el sistema de diseño.

## Actual behavior
Ver descripción.

## Evidence
Quality Gate, 2.ª pasada (subagente aislado, HEAD b778d3d). Pendiente.
