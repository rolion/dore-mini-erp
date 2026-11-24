# REV-2026-11-24-cancelar-ventas-registrar-devoluciones-04: UI-02 y ADR/DDR no reflejan lo implementado (casilla de reembolso al cancelar; ADR en «Propuesto»)

**Status:** Resolved (el usuario aprobó la desviación en el chat; PLAN v2 y DDR actualizados)
**Severity:** Low
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-11-24-cancelar-ventas-registrar-devoluciones.md (v1)
**Spec reference:** UI-02, DDR (flujo 1), PLAN (deviaciones)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
UI-02 y el DDR piden que el diálogo de cancelar muestre una casilla de reembolso (y liste los cobros a contrarrestar). La implementación mantiene el SweetAlert de motivo y agrega una segunda confirmación (`confirmRefund`) sin lista de cobros ni casilla. La desviación está solo en `docs/tasks/...md`; el PLAN y el DDR no se actualizaron y el ADR sigue en «Estado: Propuesto».

## Expected behavior
Specification/DDR consistentes con lo construido (o la UI conforme a UI-02).

## Actual behavior
Hay desviación documentada únicamente en el TASK; ninguna prueba verifica UI-02 tal como está escrita.

## Evidence
```
docs/plans/...md: «UI-02 Diálogo de cancelar con casilla de reembolso si hay cobros.»
order-detail.component.ts: confirmRefund() -> Swal.fire({... text: CANCELAR_COBROS_TEXTO(p0: paidTotal) ...})  (sin casilla ni lista)
docs/adr/ADR-cancelar-...md: «**Estado:** Propuesto»
```
