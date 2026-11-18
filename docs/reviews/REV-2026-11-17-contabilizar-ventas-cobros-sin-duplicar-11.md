# REV-2026-11-17-contabilizar-ventas-cobros-sin-duplicar-11: Falta probar un cobro concurrente con la entrega

**Status:** Resolved (prueba de cobro concurrente con la entrega)
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-17-contabilizar-ventas-cobros-sin-duplicar.md (v3)
**Spec reference:** AC-08
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
AC-08 afirma que un cobro concurrente con la entrega se serializa, pero solo se prueban dos cobros y dos entregas.

## Expected behavior
Prueba con hilos de un cobro contra una entrega: queda como anticipo aplicado o como cobro posterior, nunca perdido.

## Actual behavior
Sin prueba del caso mixto.

## Evidence
`PostingConcurrencyTests` (`test_sales_posting.py`). Hallado por el Quality Gate v3 (subagente aislado, 2026-11-17).
