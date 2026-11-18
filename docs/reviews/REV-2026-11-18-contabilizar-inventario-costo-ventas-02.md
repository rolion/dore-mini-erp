# REV-2026-11-18-contabilizar-inventario-costo-ventas-02: Faltan pruebas de casos límite y concurrencia

**Status:** Resolved (2026-11-18)
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-17-contabilizar-inventario-costo-ventas.md (v1)
**Spec reference:** AC-06, AC-10, INV-03
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El Test Specification pedía cubrir AC-06, aislamiento multiempresa de latest_averages y concurrencia; además faltan casos límite.

## Expected behavior
Pruebas de: AC-06 (sin evento de costo con stock insuficiente), aislamiento de promedios IN entre empresas, concurrencia de salidas/recepciones, producto repetido en un pedido, cantidades fraccionarias, entrega con fecha distinta de hoy, reversa de recepción tras salidas y pedido de varios productos con uno sin costo a nivel de API.

## Actual behavior
No existen.

## Evidence
Informe del Quality Gate, secciones 4 y 5 (F2).
