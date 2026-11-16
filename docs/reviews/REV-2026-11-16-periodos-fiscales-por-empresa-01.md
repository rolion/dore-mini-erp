# REV-2026-11-16-periodos-fiscales-por-empresa-01: Prueba de concurrencia dependiente de tiempos

**Status:** Open (no bloqueante)
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-16-periodos-fiscales-por-empresa.md (v1)
**Spec reference:** AC-09
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
test_closing_waits_for_the_posting_in_flight usa sleep (0.6 s / 0.2 s) para ordenar los hilos; en una CI lenta el cierre puede ganar sin que haya un bug.

## Expected behavior
Sincronizar con threading.Event (el cierre arranca cuando el asiento ya tiene el bloqueo).

## Actual behavior
Ver descripción.

## Evidence
Quality Gate (subagente aislado), backend/modules/accounting/tests/test_fiscal_period_concurrency.py:34-36. Backend 1678 OK; frontend 1430 OK (2 de 3 corridas, ver nota del flake preexistente `screens-i18n.spec.ts:58-65`, ajeno al diff).
