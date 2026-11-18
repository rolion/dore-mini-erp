# REV-2026-11-17-contabilizar-ventas-cobros-sin-duplicar-06: El enlace de la alerta no abre la pestaña «Asientos automáticos»

**Status:** Resolved (el enlace abre la pestaña «Asientos automáticos» (`?tab=posting`))
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-17-contabilizar-ventas-cobros-sin-duplicar.md (v1)
**Spec reference:** DDR › Componentes
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El enlace va a `/pocketbiz/sales/settings` sin la pestaña citada en el DDR.

## Expected behavior
Enlace a la pestaña «Asientos automáticos» o ajustar el DDR.

## Actual behavior
Funciona pero exige un clic más.

## Evidence
`order-detail.component.html:38`. Hallado por el Quality Gate (subagente aislado, 2026-11-17); suite backend 1986 OK y frontend 1574 OK.
