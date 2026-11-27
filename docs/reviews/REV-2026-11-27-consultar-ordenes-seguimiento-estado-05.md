# REV-2026-11-27-consultar-ordenes-seguimiento-estado-05: Ruta de la API incorrecta en el PLAN

**Status:** Open
**Severity:** Low
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-11-27-consultar-ordenes-seguimiento-estado.md (v2)
**Spec reference:** AC-01, API-01
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
El PLAN cita `GET /api/production/orders/`.

## Expected behavior
Ruta real `/api/production-orders/`.

## Actual behavior
Texto del plan desactualizado; código y pruebas usan la ruta real.

## Evidence
`backend/config/urls.py:30` (Quality Gate aislado, 2026-11-27).
