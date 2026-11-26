# REV-2026-11-26-lotes-disponibilidad-inventario-02: El movimiento expone lot anidado en vez de lot_id/lot_code

**Status:** Open
**Severity:** Low
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-11-26-lotes-disponibilidad-inventario.md (v1)
**Spec reference:** AC-13 / API-03
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
Contrato del movimiento distinto del escrito en PLAN/ADR.

## Expected behavior
Campos planos lot_id y lot_code (nulos sin lote).

## Actual behavior
Devuelve lot: {id, code} | null (movement_views.py:66); frontend y prueba lo asumen; no figura entre las desviaciones del TASK.

## Evidence
Cambio aditivo, no rompe nada. Resolver declarando la desviación (actualizar PLAN/ADR) o alineando el contrato.

## Resolution
Pendiente de decisión del usuario: cambiar el contrato escrito en PLAN/ADR (`lot_id`/`lot_code` planos) por `lot: {id, code}` anidado es un cambio de Specification y requiere aprobación explícita. Es aditivo; el código y el frontend ya usan el anidado.
