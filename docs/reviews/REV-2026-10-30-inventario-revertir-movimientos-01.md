# REV-2026-10-30-inventario-revertir-movimientos-01: Rutas de API del plan no coinciden con las implementadas y no se documenta la desviación

**Status:** Open
**Severity:** Low
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-10-30-inventario-revertir-movimientos.md (v1)
**Spec reference:** API-01, API-02 (y AC-01..AC-05)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
El plan nombra `POST /api/inventory/movements/<id>/reverse/` y `GET /api/inventory/movements/<id>/`. La API real de movimientos cuelga de `/api/stock-movements/`.

## Expected behavior
La Specification cita las rutas reales, o la sección «Desviaciones del plan» de la task registra la diferencia.

## Actual behavior
La implementación sigue la convención existente (correcta), pero la ruta del plan es inexistente y la task no la lista entre las desviaciones.

## Evidence
- `backend/config/urls.py:15`: `path('api/stock-movements/', include('modules.inventory.api.movement_urls'))`.
- `backend/modules/inventory/tests/test_reversal.py` usa `URL` sobre `stock-movements`.
- PLAN líneas 47, 75, 76 mencionan `/api/inventory/movements/`; TASK «Desviaciones del plan» (1)-(4) no lo menciona.
