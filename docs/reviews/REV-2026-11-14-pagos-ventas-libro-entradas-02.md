# REV-2026-11-14-pagos-ventas-libro-entradas-02: docs/architecture/ddd.md no refleja la nueva dependencia sales -> accounting

**Status:** Open
**Severity:** Low
**Category:** ARCHITECTURE
**Related plan:** docs/plans/PLAN-2026-11-14-pagos-ventas-libro-entradas.md (v1)
**Spec reference:** ADR decisión 8; plan "Files/components affected" (ddd.md "solo si cambia el mapa de dependencias")
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El diff añade `accounting` a `ALLOWED_DEPENDENCIES['sales']` (test_boundaries.py), lo que cambia el mapa de dependencias, pero `docs/architecture/ddd.md` no se actualizó.

## Expected behavior
Según el plan, ddd.md se actualiza cuando cambia el mapa de dependencias (precedente: la nota de PB-INT-002 documentó `sales -> inventory`).

## Actual behavior
`git diff --stat origin/main...HEAD` no incluye `docs/architecture/ddd.md`; la nota de PB-ACC-001 (línea ~1321) y el párrafo de dependencias permitidas (línea ~821) no mencionan `sales -> accounting`, el puerto `PaymentLedger` ni la idempotencia de pagos.

## Evidence
`git diff --stat origin/main...HEAD` (20 archivos, ninguno es ddd.md); `grep -n "PB-ACC-003" docs/architecture/ddd.md` sin resultados.
