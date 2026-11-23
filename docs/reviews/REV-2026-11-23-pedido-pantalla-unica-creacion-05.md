# REV-2026-11-23-pedido-pantalla-unica-creacion-05: Errores de `items` como lista de textos y no indexados (plan sin actualizar)

**Status:** Fixed (pendiente de re-revisión)
**Severity:** Low
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-11-23-pedido-pantalla-unica-creacion.md (v2)
**Spec reference:** API-01
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
El plan fija errores en `items[i].product_id/quantity`; se implementó `items: ["Línea N: …"]`. Está como desviación en el TASK, pero el PLAN sigue diciendo otra cosa.

## Expected behavior
Plan y código coherentes.

## Actual behavior
Ver evidencia.

## Evidence
`placement.py` (`_valid_lines`). Requiere una versión v2 del PLAN que lo recoja (cambio de contrato: aprobación del usuario).

## Resolución
API-01 y los edge cases describen la lista de textos «Línea N: …» que ya implementa el código (PLAN v2, aprobado por el usuario).
