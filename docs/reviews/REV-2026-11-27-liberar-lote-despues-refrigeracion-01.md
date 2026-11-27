# REV-2026-11-27-liberar-lote-despues-refrigeracion-01: Tests de Modularidad rotos por el tipo integer

**Status:** Resolved
**Severity:** High
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-27-liberar-lote-despues-refrigeracion.md (v1)
**Spec reference:** AC-07
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El catálogo de ajustes ganó el tipo `integer` y la clave de producción, pero `test_settings_domain.py` no se actualizó.

## Expected behavior
Los tests de dominio de ajustes pasan.

## Actual behavior
2 fallos.

## Evidence
`FAIL: test_catalog_is_coherent` — AssertionError: 'integer' not found in ('choice', 'percent', 'boolean'); `FAIL: test_documented_initial_values` — sobra 'production.min_refrigeration_hours': '12' (Quality Gate ciclo 1).

## Resolución
Actualizados ambos tests; `modules.modularity.tests.test_settings_domain`, `test_domain` y `test_order_domain`: 37 OK.
