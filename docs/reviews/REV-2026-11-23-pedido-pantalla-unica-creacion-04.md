# REV-2026-11-23-pedido-pantalla-unica-creacion-04: Pruebas planificadas sin escribir

**Status:** Open
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
