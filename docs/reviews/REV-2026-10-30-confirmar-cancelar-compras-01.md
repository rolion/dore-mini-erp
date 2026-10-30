# REV-2026-10-30-confirmar-cancelar-compras-01: Falta la prueba de ida y vuelta de los campos de ciclo de vida

**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-30-confirmar-cancelar-compras.md (v1)
**Spec reference:** INV-08, EDGE-07, AC-10
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
La Test Specification pide ampliar `test_purchase_repository.py` con la ida y vuelta de `confirmed_at`, `cancelled_at`, `cancellation_reason`, `reception_status` y `payment_status` (y sus valores por defecto). No existe y no se declaró como desviación en el TASK.

## Expected behavior
Una prueba con BD guarda y relee una compra confirmada y una cancelada y comprueba los cinco campos.

## Actual behavior
`grep -E "confirmed_at|reception_status|cancel" backend/modules/purchases/tests/test_purchase_repository.py` no devuelve nada; el mapper solo queda cubierto indirectamente por las pruebas de API, que requieren PostgreSQL.

## Evidence
Informe del Quality Gate (grep vacío). No bloquea: el mapper se revisó por lectura y la API lo ejercita.
