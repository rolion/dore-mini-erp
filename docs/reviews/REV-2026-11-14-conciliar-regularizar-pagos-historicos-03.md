# REV-2026-11-14-conciliar-regularizar-pagos-historicos-03: Tras aplicar, una nueva previsualización fallida muestra el resultado aplicado con el aviso «no se ha escrito nada»

**Status:** Resolved
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-14-conciliar-regularizar-pagos-historicos.md (v2)
**Spec reference:** UI-03, UI-05, AC-16, AC-17
**Plan mode:** COMPLETO
**Suggested owner:** delivery-frontend / delivery-build

## Description
En `RegularizationComponent.preview()` se hace `this.applied = false` antes de la petición, pero `this.summary` conserva el resumen del modo `apply` anterior. La plantilla decide el aviso con `@if (applied)`.

## Expected behavior
Un resumen de resultado de aplicación nunca se presenta como previsualización. Mientras se previsualiza de nuevo, o si la previsualización falla (400/409/red), se oculta o se mantiene el resultado con su aviso de éxito; jamás «no se ha escrito nada» sobre datos que sí se escribieron.

## Actual behavior
Flujo: previsualizar, aplicar (resultado «N creadas»), cambiar el formulario, «Previsualizar». Durante la petición y, si falla, después de ella, la tarjeta Resumen muestra los grupos `created/existing/failed` del resultado aplicado bajo el `alert alert-info` «no se ha escrito nada» (`AVISO_PREVISUALIZACION`). Aplicar queda deshabilitado (no hay `missing`), así que no hay riesgo de doble escritura; el daño es un mensaje falso en una pantalla de dinero.

## Evidence
`regularization.component.ts` `preview()`: `this.errors = []; this.applied = false;` sin tocar `this.summary`; `regularization.component.html`: `@if (applied) { ...result... } @else { ...AVISO_PREVISUALIZACION... }`. Lectura de código; ninguna prueba cubre apply seguido de una previsualización fallida (`regularization.component.spec.ts`).
