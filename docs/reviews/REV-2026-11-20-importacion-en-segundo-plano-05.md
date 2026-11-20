# REV-2026-11-20-importacion-en-segundo-plano-05: El servicio import-worker no tiene healthcheck

**Status:** Open
**Severity:** Low
**Category:** ARCHITECTURE
**Related plan:** docs/plans/PLAN-2026-11-20-importacion-en-segundo-plano.md (v1)
**Spec reference:** AC-11
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
`docker compose up -d --wait` solo confirma que el contenedor esta en ejecucion.

## Expected behavior
El despliegue deberia detectar un worker que cae en bucle.

## Actual behavior
Las corridas quedarian en cola sin aviso (riesgo ya documentado en el ADR).

## Evidence
`compose.yaml` `import-worker` sin `healthcheck`.
