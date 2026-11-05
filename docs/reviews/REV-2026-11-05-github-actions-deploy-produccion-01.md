# REV-2026-11-05-github-actions-deploy-produccion-01: El migrate consume el stdin del script

**Status:** Resolved (pendiente de re-verificación)
**Severity:** High
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-05-github-actions-deploy-produccion.md (v1)
**Spec reference:** AC-04 / INV-01 / INV-02
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`docker compose run` reenvía stdin y, con `bash -s`, se traga el resto del script: migra pero no levanta la versión y el job puede salir verde.

## Expected behavior
El pipeline completa migración, levantado y smoke check, o aborta sin tocar la versión en ejecución.

## Actual behavior
Ver Description (reproducido por el revisor con simulaciones bash; no había Docker disponible).

## Evidence
scripts/deploy/remote-deploy.sh:72. Reporte del Quality Gate (subagente aislado), ciclo 1: FAIL.

## Resolución
Se evalúa el script tras leer todo el stdin (`payload=$(cat); eval`), `-T` y `</dev/null` en cada docker. Prueba con docker falso.
