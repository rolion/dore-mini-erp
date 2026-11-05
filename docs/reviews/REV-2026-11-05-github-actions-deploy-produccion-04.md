# REV-2026-11-05-github-actions-deploy-produccion-04: Pruebas no cubren orden/abortos de AC-04, INV-01, INV-02

**Status:** Closed (verificado en ciclo 2)
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-05-github-actions-deploy-produccion.md (v1)
**Spec reference:** AC-04 / INV-01 / INV-02
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`test_step_order` solo compara posiciones de texto.

## Expected behavior
El pipeline completa migración, levantado y smoke check, o aborta sin tocar la versión en ejecución.

## Actual behavior
Ver Description (reproducido por el revisor con simulaciones bash; no había Docker disponible).

## Evidence
backend/config/test_deploy_pipeline.py. Reporte del Quality Gate (subagente aislado), ciclo 1: FAIL.

## Resolución
Pruebas que ejecutan el script con docker falso: orden, backup fallido => sin migrate, migrate fallido => sin up.
