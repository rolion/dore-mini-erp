# REV-2026-11-16-motor-central-asientos-partida-doble-01: Falta la prueba de migración 0010 prevista en el PLAN

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-16-motor-central-asientos-partida-doble.md (v1)
**Spec reference:** PLAN > Test Specification > Integration tests (Migración 0010); Files affected (test_migration_0010.py)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El PLAN exige una prueba de migración 0010 (aplica/revierte sobre datos existentes, sin tocar accounting_entry) y lista `accounting/tests/test_migration_0010.py`.

## Expected behavior
Existe `test_migration_0010.py` y la sección Implementación del TASK declara cualquier omisión.

## Actual behavior
El archivo no existe y la sección Implementación del TASK no declara la omisión ni lo lista en «Pruebas añadidas».

## Evidence
`ls backend/modules/accounting/tests | grep migration` no devuelve `test_migration_0010`. El revisor aplicó y revirtió la migración a mano en una base temporal (migrate completo, `migrate accounting 0009` deja 0 tablas accounting_journal*, re-migrate deja 2): funciona, pero no queda como prueba automatizada.
