# REV-2026-11-23-pedido-pantalla-unica-creacion-02: Suite backend contra PostgreSQL no ejecutada

**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-23-pedido-pantalla-unica-creacion.md (v1)
**Spec reference:** INV-06, AC-08
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
No hay credenciales de PostgreSQL en la máquina de revisión; solo se corrió con SQLite como aproximación. Quedan sin confirmar el rollback total, `select_for_update` y la concurrencia sobre una BD real.

## Expected behavior
`manage.py test modules.sales modules.modularity` verde en PostgreSQL.

## Actual behavior
Ver evidencia.

## Evidence
SQLite: HEAD 493 pruebas, 4 failures y 64 errores (`pg_advisory_xact_lock`, `pg_locks`, tablas bloqueadas); en `origin/main` 475 pruebas, 5 failures y 64 errores. El conjunto de fallos de HEAD es subconjunto del de base; las 18 pruebas nuevas y `test_api` (106) pasan. Pendiente en CI u otra máquina.
