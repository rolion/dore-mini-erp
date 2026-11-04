# REV-2026-11-04-presentar-aceptar-versionar-proformas-02: Spec preexistente de idioma falla fuera del alcance

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-04-presentar-aceptar-versionar-proformas.md (v1)
**Spec reference:** N/A (preexistente, no tocado por este task)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`src/app/core/i18n/screens-i18n.spec.ts` («labels coming from code follow the active language») falla también ejecutada sola; compara `ORDER_STATUS_LABELS.DELIVERED` de Ventas, que este task no modifica. La base apilada está 15 commits por detrás de `main` (donde se refinó la UX de Pedidos).

## Expected behavior
La suite completa del frontend pasa.

## Actual behavior
`TOTAL: 1 FAILED, 1238 SUCCESS`; `Expected 'Delivered' to be 'Entregado'` en `screens-i18n.spec.ts:60`.

## Evidence
`ng test --watch=false --browsers=ChromeHeadless` (1239 specs) y, aislado, `--include=src/app/core/i18n/screens-i18n.spec.ts` → `TOTAL: 1 FAILED, 2 SUCCESS`. Sin cambios del task en Ventas ni en `core/i18n`. Se espera que se resuelva al integrar `main` en la base.
