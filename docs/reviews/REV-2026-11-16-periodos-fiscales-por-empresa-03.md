# REV-2026-11-16-periodos-fiscales-por-empresa-03: Aserción debilitada en la carrera cierre vs. asiento

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-16-periodos-fiscales-por-empresa.md (v1)
**Spec reference:** AC-09
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Acepta ambos órdenes y no inserta una fila real bajo lock_open_period (se difiere a CONT-02, declarado).

## Expected behavior
Opcional: hacer determinista el caso «cierre gana».

## Actual behavior
Ver descripción.

## Evidence
Quality Gate (subagente aislado), test_fiscal_period_concurrency.py:38-44. Backend 1678 OK; frontend 1430 OK (2 de 3 corridas, ver nota del flake preexistente `screens-i18n.spec.ts:58-65`, ajeno al diff).
