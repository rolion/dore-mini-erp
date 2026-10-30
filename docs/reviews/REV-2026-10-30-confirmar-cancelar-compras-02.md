# REV-2026-10-30-confirmar-cancelar-compras-02: Rutas confirm/cancel sin registrar en la guarda de módulos

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-30-confirmar-cancelar-compras.md (v1)
**Spec reference:** AC-11
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`modularity/tests/test_enforcement.py` no lista las rutas nuevas `confirm/` y `cancel/`, y la prueba de API solo comprueba el 403 por módulo deshabilitado para `confirm`, no para `cancel`. Ambas vistas declaran `required_modules`.

## Expected behavior
Ambas rutas cubiertas por la guarda de módulos deshabilitados.

## Actual behavior
Cobertura parcial (solo `confirm`, solo en la prueba de API).

## Evidence
Informe del Quality Gate. Hallazgos informativos H-03, H-04 y H-05 del informe no requieren acción (referencia desactualizada a `test_guards` en el plan; `nav-tabs` estático ya documentado en el design-system; `cancel` repetido sin validar motivo es coherente con INV-07).

## Resolution
Corregido por delivery-build (2026-10-30): rutas `confirm/` y `cancel/` agregadas a `modularity/tests/test_enforcement.py` (403 sin el módulo).
