# REV-2026-11-17-contabilizar-ventas-cobros-sin-duplicar-07: Seis líneas nuevas superan 120 caracteres

**Status:** Resolved (líneas largas ajustadas (ninguna línea nueva supera 120))
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-17-contabilizar-ventas-cobros-sin-duplicar.md (v1)
**Spec reference:** Estilo
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Líneas largas en `views.py`, `commands.py`, `ports.py` y `adapters.py`.

## Expected behavior
Máximo 120 caracteres.

## Actual behavior
No hay linter instalado para verificarlo automáticamente.

## Evidence
Ver diff de `backend/modules/sales`. Hallado por el Quality Gate (subagente aislado, 2026-11-17); suite backend 1986 OK y frontend 1574 OK.
