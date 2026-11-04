# REV-2026-11-03-crear-proformas-de-servicios-08: La página de detalle (presentar, nueva versión) no tiene specs

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-03-crear-proformas-de-servicios.md (v2)
**Spec reference:** Test Specification (AC-11: "specs de servicio/componentes"); REV-07 (marcado Resolved)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
REV-07 pedía specs de las tres páginas. Se añadieron los de formulario y lista, pero no existe `proforma-detail.component.spec.ts`; el detalle concentra la acción de mayor riesgo (presentar, inmutable) y «Nueva versión».

## Expected behavior
Specs del detalle que cubran: acciones visibles según `allowed_actions`; diálogo «Presentar» (éxito cierra y actualiza estado; error 400/409 se muestra en el diálogo; doble envío bloqueado por `saving`); «Nueva versión» navega a `/editar` del borrador y muestra el error 409.

## Actual behavior
`ng test` acotado a quotations: 22/22 OK, pero la cobertura de `features/quotations` solo lista form (75 % sentencias / 81 % líneas), list (94 %) y api service (78 %) y models (100 %); `proforma-detail.component.ts` no aparece (0 %, sin spec).

## Evidence
`frontend/panel_admin/src/app/features/quotations/pages/` contiene `proforma-detail.component.ts` sin `.spec.ts`; informe de cobertura `coverage/oreva/app/features/quotations/pages/index.html` solo incluye form y list.
