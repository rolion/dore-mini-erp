# REV-2026-11-23-pedido-pantalla-unica-creacion-01: Espacio perdido en urls.py (flake8 E231)

**Status:** Fixed (pendiente de re-revisión)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-23-pedido-pantalla-unica-creacion.md (v1)
**Spec reference:** N/A
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`backend/modules/sales/api/urls.py:23` perdió el espacio tras la coma en `path('<str:order_id>/',OrderDetailView…)`.

## Expected behavior
Cero avisos de lint en líneas nuevas.

## Actual behavior
Ver evidencia.

## Evidence
`flake8`: `modules/sales/api/urls.py:23:27: E231 missing whitespace after ','`.

## Resolución
`urls.py` recupera el espacio; `flake8` sin avisos nuevos.
