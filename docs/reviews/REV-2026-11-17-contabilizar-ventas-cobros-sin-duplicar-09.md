# REV-2026-11-17-contabilizar-ventas-cobros-sin-duplicar-09: Parámetro `available` sin uso en `FakeLedger`

**Status:** Resolved (parámetro sin uso eliminado de `FakeLedger`)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-17-contabilizar-ventas-cobros-sin-duplicar.md (v1)
**Spec reference:** Limpieza
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Tras eliminar una prueba, `FakeLedger(available=...)` quedó sin uso.

## Expected behavior
Sin parámetros muertos.

## Actual behavior
Código de prueba residual.

## Evidence
`test_payment_ledger.py`. Hallado por el Quality Gate (subagente aislado, 2026-11-17); suite backend 1986 OK y frontend 1574 OK.
