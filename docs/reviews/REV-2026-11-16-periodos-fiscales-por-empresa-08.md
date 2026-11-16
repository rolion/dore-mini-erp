# REV-2026-11-16-periodos-fiscales-por-empresa-08: PATCH de un período cerrado con límites idénticos responde 409

**Status:** Open (no bloqueante)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-16-periodos-fiscales-por-empresa.md (v1)
**Spec reference:** INV-05
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Coherente con INV-05; informativo.

## Expected behavior
Sin acción.

## Actual behavior
Ver descripción.

## Evidence
Quality Gate (subagente aislado), application/fiscal_periods.py (UpdateFiscalPeriod). Backend 1678 OK; frontend 1430 OK (2 de 3 corridas, ver nota del flake preexistente `screens-i18n.spec.ts:58-65`, ajeno al diff).
