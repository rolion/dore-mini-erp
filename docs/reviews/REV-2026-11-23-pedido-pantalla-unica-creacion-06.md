# REV-2026-11-23-pedido-pantalla-unica-creacion-06: Almacén guardado inactivo: la entrega y la vista previa se comportan distinto; nombre vacío

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-23-pedido-pantalla-unica-creacion.md (v1)
**Spec reference:** AC-07, API-02
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Si el almacén guardado se desactiva, `DeliverOrder` lo usa igual y `PreviewOrderDelivery` sugiere otro. Además `warehouse.name` sale vacío porque solo se consultan almacenes activos.

## Expected behavior
Criterio coherente entre vista previa y entrega, y nombre disponible.

## Actual behavior
Ver evidencia.

## Evidence
`commands.py:230`, `delivery.py`, `views.py` (`_order_response`).
