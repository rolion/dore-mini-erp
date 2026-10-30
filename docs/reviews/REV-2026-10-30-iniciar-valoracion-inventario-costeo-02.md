# REV-2026-10-30-iniciar-valoracion-inventario-costeo-02: Confirmación de la adopción sin alert-success (el DDR lo indica)

**Status:** Resolved
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-10-30-iniciar-valoracion-inventario-costeo.md (v1)
**Spec reference:** UI-05, AC-10; DDR sección «Comportamiento por privilegio/estado»
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El DDR define el estado de éxito como «consulta con `alert-success`». Al confirmar, la página cambia a la consulta y solo muestra un toast (`toastr.success('Valoración adoptada')`); en la vista de consulta no hay `alert-success` persistente.

## Expected behavior
Coherencia con el DDR: o bien un `alert alert-success` tras adoptar en la consulta, o bien actualizar el DDR para indicar que el éxito se comunica con toast (patrón de `stock-opening`, que también usa `ToastrService`).

## Actual behavior
Solo toast efímero; el título «Valoración inicial adoptada» y el resumen indican el estado, por lo que el impacto funcional es mínimo.

## Evidence
valuation.component.ts:308 (`this.toastr.success(ADOPTION_SUCCESS_MESSAGE)`); valuation.component.html no contiene `alert-success`; DDR-iniciar-valoracion-inventario-costeo-asistente-valoracion.md línea «Estados». Se puede resolver también como ajuste de documento (delivery-start).
