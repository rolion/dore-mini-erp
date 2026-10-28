# REV-2026-10-28-inventario-movimientos-trazables-03: Huecos de prueba: zona horaria de filtros de fecha, reversión concurrente y puerto del almacén

**Status:** Resolved (verificado por delivery-publish, ciclo 2)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-28-inventario-movimientos-trazables.md (v1)
**Spec reference:** AC-05, EDGE-03, INV-07, AC-09
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Cobertura incompleta de comportamientos de riesgo.

## Expected behavior
Pruebas que fijen: (a) el filtro `date_from/date_to` en el límite de día según `TIME_ZONE` (el repositorio usa `occurred_at__date__gte/lte`, que convierte a la zona activa); (b) dos reversiones simultáneas del mismo movimiento dejan un solo contramovimiento (la restricción `inv_mov_one_reversal_uniq` y el bloqueo existen pero no se prueban; EDGE-03 solo se prueba secuencial); (c) reversión de un contramovimiento por la fachada (`cannot_reverse_reversal` solo se prueba en dominio).

## Actual behavior
`test_filters` (`tests/test_movements.py:315-335`) solo prueba fechas lejanas (UTC, sin límites de día); `ConcurrencyTests` no cubre reversiones; no hay test del caso «reintento de operación ya revertida».

## Evidence
`backend/modules/inventory/tests/test_movements.py` (sin `TIME_ZONE` override ni test de reversión concurrente). Los 743 tests pasan; no hay fallo, solo huecos.
