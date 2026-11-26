# REV-2026-11-26-lotes-disponibilidad-inventario-04: Prueba de carrera del mismo origen no verifica que no se gaste número

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-26-lotes-disponibilidad-inventario.md (v1)
**Spec reference:** AC-02
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
La prueba solo afirma un lote.

## Expected behavior
También que el siguiente número no tenga huecos.

## Actual behavior
test_the_same_source_created_at_once_makes_one_lot solo comprueba count()==1.

## Evidence
backend/modules/inventory/tests/test_lots_concurrency.py
