# REV-2026-11-17-contabilizar-ventas-cobros-sin-duplicar-13: Archivos fuera del PLAN v3

**Status:** Open
**Severity:** Low
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-11-17-contabilizar-ventas-cobros-sin-duplicar.md (v3)
**Spec reference:** Files affected
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
`methods-tab.component.scss` (interruptor clicable, pedido por la persona) y `find_automatic_entry` en la fachada no figuran en «Files affected».

## Expected behavior
Reflejarlos en el PLAN/TASK.

## Actual behavior
Justificados y con prueba (`FindTests`), solo falta documentarlos.

## Evidence
Commit 24723a3 y `accounting/services.py`. Hallado por el Quality Gate v3 (subagente aislado, 2026-11-17).
