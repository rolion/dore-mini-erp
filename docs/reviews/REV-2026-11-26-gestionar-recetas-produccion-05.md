# REV-2026-11-26-gestionar-recetas-produccion-05: Huecos de prueba backend

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-26-gestionar-recetas-produccion.md (v1)
**Spec reference:** Test Specification
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Faltan pruebas de la búsqueda `q`, de `product_active` (EDGE-05) en la API, de más de 4 decimales vía API, de `page_size` inválido/página fuera de rango y de ausencia de N+1 en la lista.

## Expected behavior
Cada rama nueva con prueba.

## Actual behavior
Sin esas pruebas.

## Evidence
`modules/production/tests/test_api.py`.
