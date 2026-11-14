# REV-2026-11-05-github-actions-deploy-produccion-02: La poda aborta el script con pipefail

**Status:** Closed (verificado en ciclo 2)
**Severity:** High
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-05-github-actions-deploy-produccion.md (v1)
**Spec reference:** AC-04 / INV-01 / INV-02
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`grep -v` sale con 1 si no queda nada que podar; con `set -euo pipefail` el deploy termina en rojo antes del mensaje final y del smoke check.

## Expected behavior
El pipeline completa migración, levantado y smoke check, o aborta sin tocar la versión en ejecución.

## Actual behavior
Ver Description (reproducido por el revisor con simulaciones bash; no había Docker disponible).

## Evidence
scripts/deploy/remote-deploy.sh:79-84. Reporte del Quality Gate (subagente aislado), ciclo 1: FAIL.

## Resolución
`{ grep -v ... || true; }`. Prueba del camino feliz sin nada que podar.
