# REV-2026-11-18-contabilizar-inventario-costo-ventas-03: Observaciones menores del Quality Gate

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-17-contabilizar-inventario-costo-ventas.md (v1)
**Spec reference:** NFR del plan / estilo
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
(a) get_product_totals filtra en memoria todos los saldos de la empresa (inventory/services.py:253-260); (b) occurred_at del evento de costo usa timezone.now() aunque el asiento usa delivered_date; (c) E128 en sales/api/views.py:248 y E501 en la migración 0002 (líneas 32-33, generada); (d) tras revertir la única recepción el promedio sigue siendo el de esa recepción (coherente con AC-07, a documentar como límite).

## Expected behavior
Consulta acotada por producto, fecha del evento coherente con la del asiento y cero avisos nuevos de estilo.

## Actual behavior
Ver descripción.

## Evidence
Quality Gate: flake8 sobre el diff; revisión de código (F3-F6).
