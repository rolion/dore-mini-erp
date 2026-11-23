# REV-2026-11-23-pedido-pantalla-unica-creacion-04: Pruebas planificadas sin escribir

**Status:** Fixed (pendiente de re-revisión)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-23-pedido-pantalla-unica-creacion.md (v1)
**Spec reference:** INV-01, INV-07, AC-07, AC-09, AC-10
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Faltan: producto repetido en el cuerpo (rama `seen`), Clientes deshabilitado en backend, cliente de otra empresa, prueba unitaria de dominio de `assign_warehouse`, y spec del almacén en `order-detail` o `delivery-dialog`.

## Expected behavior
Tabla «Acceptance criteria mapping» completa.

## Actual behavior
Ver evidencia.

## Evidence
`backend/modules/sales/tests/test_place_order.py` no cubre esos casos.

## Resolución
Pruebas añadidas: producto repetido en el cuerpo, cliente de otra empresa, Clientes deshabilitado, almacén guardado inactivo en la entrega (`test_place_order.py`), dominio de `assign_warehouse` (`test_order_warehouse.py`) y fila de almacén en `order-detail`. El diálogo de entrega no cambió, por lo que no se añadió spec propio.
