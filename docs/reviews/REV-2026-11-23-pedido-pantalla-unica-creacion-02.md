# REV-2026-11-23-pedido-pantalla-unica-creacion-02: Suite backend contra PostgreSQL no ejecutada

**Status:** Fixed (verificado)
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

## Resolución
Suite completa contra PostgreSQL (`DJANGO_SETTINGS_MODULE=config.settings.test`, serie, base libre): `Ran 2387 tests in 415.851s` → `FAILED (failures=4)`. Los 4 fallos son de `config.test_deploy_pipeline` (`test_happy_path_runs_all_steps_even_with_nothing_to_prune`, `test_database_url_is_composed_and_encoded`, `test_missing_variables_fail_early`, `test_syntax`) con `execvpe(/bin/bash) failed: No such file or directory`: esta máquina Windows no tiene `/bin/bash`; el diff no toca despliegue ni configuración. Un intento previo salió contaminado por otra sesión que usaba la misma base `test_doredb` y se descartó.
