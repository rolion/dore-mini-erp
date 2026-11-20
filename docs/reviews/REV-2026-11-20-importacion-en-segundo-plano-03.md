# REV-2026-11-20-importacion-en-segundo-plano-03: Pruebas mas debiles que la tabla AC -> verificacion del plan

**Status:** Resolved
**Severity:** Medium
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-11-20-importacion-en-segundo-plano.md (v1)
**Spec reference:** AC-03, AC-05, AC-07, AC-08
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
AC-03 (progreso durante la corrida) solo en unit con fakes; AC-07 es secuencial (declarado en el TASK); AC-08 no tiene dos empresas con corridas en cola a la vez; AC-05 sin integracion de "modulo deshabilitado tras encolar".

## Expected behavior
Cada AC con la verificacion asignada en el plan (incluye `Barrier`/hilos para AC-07 y dos empresas para AC-08).

## Actual behavior
Los comportamientos se cumplen por lectura del codigo pero no estan probados de punta a punta.

## Evidence
Informe del Quality Gate: `test_a_queued_run_is_claimed_only_once` sin hilos; `test_other_company_cannot_see_the_run_and_the_worker_uses_the_runs_company` con una sola empresa encolada.

## Resolución
Corregido en el commit de seguimiento del 2026-11-20 (repositorio y pruebas de integración con hilos, dos empresas y progreso); pruebas de `modules.data_import` en verde con PostgreSQL 16.
