# REV-2026-11-16-diagnostico-transicion-partida-doble-01: Ensayo en copia de la base local no ejecutado

**Status:** Closed (2026-11-16)
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-16-diagnostico-transicion-partida-doble.md (v1)
**Spec reference:** AC-08 (segunda mitad; aceptación 2 de la tarjeta)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build (ejecución manual por una persona con acceso a PostgreSQL)

## Description
AC-08 exige que una copia restaurada de la base local aplique `migrate` sin cambios y que el diagnóstico dé los mismos importes antes y después.

## Expected behavior
Evidencia de `pg_dump` → `pg_restore` en otra base → `migrate` → `diagnose_ledger_transition` antes/después con importes idénticos.

## Actual behavior
No se pudo ejecutar: la máquina no tiene `pg_dump`, `pg_restore`, `createdb` ni `psql` en el PATH. Sí se verificó: base de pruebas creada desde cero con toda la cadena de migraciones (aceptación 1) y `makemigrations --check` sin cambios.

## Evidence
`which pg_dump pg_restore createdb psql` → `no pg_dump in (...)`, idem para los otros tres.
`manage.py test modules.accounting modules.sales.tests.test_boundaries` → `Ran 181 tests ... OK`.
`manage.py makemigrations --check --dry-run` → `No changes detected`.

## Resolución
Ensayo ejecutado con PostgreSQL 16: `pg_dump` → `pg_restore` en `doredb_copia` → diagnóstico antes (idéntico a la original) → `migrate` («No migrations to apply») → diagnóstico después (idéntico). 32 entradas, 4 448,50. Ver `docs/deployment/transicion-partida-doble.md`.
