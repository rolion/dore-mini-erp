# REV-2026-11-23-pedido-pantalla-unica-creacion-07: `placement.py` importa un helper privado de `commands.py`

**Status:** Accepted (deuda técnica)
**Severity:** Low
**Category:** ARCHITECTURE
**Related plan:** docs/plans/PLAN-2026-11-23-pedido-pantalla-unica-creacion.md (v1)
**Spec reference:** N/A
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
`from .commands import _customer_errors`.

## Expected behavior
Helper compartido público o en un módulo común.

## Actual behavior
Ver evidencia.

## Evidence
`backend/modules/sales/application/placement.py:15`. No viola DDD.

## Resolución
Aceptado como deuda técnica por el usuario (2026-11-23); sin cambio de código en esta tarea.
