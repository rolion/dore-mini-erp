# REV-2026-11-20-importacion-en-segundo-plano-02: finish() y fail() actualizan sin condicion de estado

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-20-importacion-en-segundo-plano.md (v1)
**Spec reference:** INV-12
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Si una venta tarda >15 min sin latido, `fail_stale` marca la corrida `FAILED interrupted` mientras el worker sigue y luego esta sobrescribe a COMPLETED/FAILED.

## Expected behavior
Una corrida ya marcada FAILED por interrupcion no debe volver a COMPLETED.

## Actual behavior
Sobrescritura posible (improbable; sin duplicados gracias a INV-05).

## Evidence
`repositories.py` `finish`/`fail` sin `filter(status=RUNNING)`.

## Resolución
Corregido en el commit de seguimiento del 2026-11-20 (repositorio y pruebas de integración con hilos, dos empresas y progreso); pruebas de `modules.data_import` en verde con PostgreSQL 16.
