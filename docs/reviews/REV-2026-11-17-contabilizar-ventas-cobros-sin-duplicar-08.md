# REV-2026-11-17-contabilizar-ventas-cobros-sin-duplicar-08: El ADR no refleja las firmas ni el orden reales

**Status:** Resolved (nota de reconciliación en el ADR)
**Severity:** Low
**Category:** ARCHITECTURE
**Related plan:** docs/plans/PLAN-2026-11-17-contabilizar-ventas-cobros-sin-duplicar.md (v1)
**Spec reference:** ADR §1-§2
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
El ADR habla de `check_posting_ready` previo y de `covers(date)`; la implementación transiciona y luego `recognize` (rollback por `_run`), y no existe `covers`.

## Expected behavior
Reconciliar el texto del ADR con las firmas (`today` como argumento, `reverse_recognition(order, reason, actor, today)`).

## Actual behavior
Equivalente en comportamiento (prueba de período cerrado).

## Evidence
`ADR-contabilizar-ventas-cobros-sin-duplicar-puerto-reconocimiento-y-cobro.md`. Hallado por el Quality Gate (subagente aislado, 2026-11-17); suite backend 1986 OK y frontend 1574 OK.
