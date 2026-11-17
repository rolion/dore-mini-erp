# REV-2026-11-17-contabilizar-ventas-cobros-sin-duplicar-05: Falta spec del flujo de cobro con `issues` y `order-payments` no cambió

**Status:** Open (Gate v3: el spec existente usa `prepare`, que ya no puede devolver `posting_configuration_missing`; falta el spec del cobro y actualizar el comentario de `PostingIssue`)
**Severity:** Low
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-11-17-contabilizar-ventas-cobros-sin-duplicar.md (v1)
**Spec reference:** AC-14 / Files affected
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
La alerta vive en `order-detail` (el cobro pasa por `run()`), pero solo hay spec de «confirmar».

## Expected behavior
Spec del cobro con `posting_configuration_missing`.

## Actual behavior
`order-detail.component.spec.ts` cubre solo `runPrimary`.

## Evidence
`order-detail.component.spec.ts`. Hallado por el Quality Gate (subagente aislado, 2026-11-17); suite backend 1986 OK y frontend 1574 OK.
