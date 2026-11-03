# REV-2026-10-30-valorar-recepciones-consumos-costo-historico-03: Pruebas de API-04 laxas y entrega de pedido sin prueba de extremo a extremo

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-30-valorar-recepciones-consumos-costo-historico.md (v1)
**Spec reference:** API-04, AC-03, AC-09
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
(1) `test_reverting_a_receipt_is_blocked_when_a_later_consumption_used_its_cost` acepta `400` o `409` (`assertIn(status, (400, 409))`) y comprueba solo la palabra «posteriores»; API-04 y AC-09 fijan 409 `valuation_blocked`. (2) AC-03 (entrega de pedido) se prueba llamando `inventory.record_outputs` directamente, no con la entrega real de Ventas (el plan pide «integración entrega»). (3) No hay prueba de la reversión por la API de movimientos (`ReverseMovement`) con valoración.

## Expected behavior
Prueba que fije el código HTTP y el `code` exacto del bloqueo de reversión, y una entrega de pedido real que deje el snapshot.

## Actual behavior
El código de estado y el `code` de error de la reversión bloqueada no están fijados por ninguna prueba; el mapeo en Compras/Ventas de `valuation_blocked` puede cambiar sin que falle la suite.

## Evidence
backend/modules/costing/tests/test_movement_valuation.py:151 (`self.assertIn(response.status_code, (400, 409), response.content)`); línea 96-99 (`out()` usa `inventory.record_outputs`).
