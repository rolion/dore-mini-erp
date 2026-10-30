# REV-2026-10-30-integracion-recepciones-entradas-inventario-01: AC-15 sin prueba real de reintento con el mismo receipt_id ni de ausencia de mensaje de éxito

**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-30-integracion-recepciones-entradas-inventario.md (v1)
**Spec reference:** AC-15; Test Specification (reception-form.component.spec.ts)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build (frontend)

## Description
El plan mapea AC-15 a reception-form.component.spec.ts con «sin éxito parcial ante error con receipt_id reutilizado».

## Expected behavior
Una prueba que, tras un error de confirmación, verifique que no hay toast/mensaje de éxito y que el reintento envía el mismo receiptId.

## Actual behavior
Las pruebas de 400 y 409 (líneas 224-257) verifican que se conservan los datos y el estado de edición, pero ninguna reintenta la confirmación ni compara receiptId entre llamadas; el único assert de receiptId (línea 139) solo comprueba el formato UUID. Tampoco se afirma la ausencia de toast.

## Evidence
frontend/panel_admin/src/app/features/purchases/pages/reception-form/reception-form.component.spec.ts:139,224-257. El diff del spec solo añade asserts de textos (AC-12).
