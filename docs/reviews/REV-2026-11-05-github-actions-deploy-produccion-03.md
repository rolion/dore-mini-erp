# REV-2026-11-05-github-actions-deploy-produccion-03: workflow_dispatch puede desplegar cualquier rama

**Status:** Closed (verificado en ciclo 2)
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-05-github-actions-deploy-produccion.md (v1)
**Spec reference:** AC-04 / INV-01 / INV-02
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Sin restricción de ref, otra rama podría desplegar a producción.

## Expected behavior
El pipeline completa migración, levantado y smoke check, o aborta sin tocar la versión en ejecución.

## Actual behavior
Ver Description (reproducido por el revisor con simulaciones bash; no había Docker disponible).

## Evidence
deploy.yml (job). Reporte del Quality Gate (subagente aislado), ciclo 1: FAIL.

## Resolución
`if: github.ref == 'refs/heads/main'`; guía recomienda restringir Deployment branches.
