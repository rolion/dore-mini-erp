# REV-2026-11-26-gestionar-recetas-produccion-01: Contrato API en snake_case, no camelCase

**Status:** Open
**Severity:** Medium
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-11-26-gestionar-recetas-produccion.md (v1)
**Spec reference:** API-01..API-05
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
La Specification (API-01..05) describe campos camelCase; la API usa snake_case, coherente con Catálogo (`base_unit_id`). El TASK afirma «sin tocar la Specification».

## Expected behavior
Contrato y TASK coherentes: o API-01..05 enmendados, o la API en camelCase.

## Actual behavior
API: `result_product`, `yield_quantity`, `result_product_id`, `product_id`, `created_at`.

## Evidence
`api/serializers.py`, `api/views.py::_serialize`, `recipes-api.service.ts::toBody/fromDto`. Cambiar la Specification requiere aprobación explícita del usuario.
