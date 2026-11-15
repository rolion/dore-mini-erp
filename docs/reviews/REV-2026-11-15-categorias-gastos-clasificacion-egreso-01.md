# REV-2026-11-15-categorias-gastos-clasificacion-egreso-01: UI-03 sin implementar: falta el enlace de ayuda en los formularios

**Status:** Resolved (pendiente de re-verificación por el Quality Gate)
**Severity:** Medium
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-11-15-categorias-gastos-clasificacion-egreso.md (v1)
**Spec reference:** UI-03
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
El plan pide mostrar «Configurar en Contabilidad → Egresos» en los formularios de gasto y de pago de compra ante `classification_not_configured`/`classification_invalid`.

## Expected behavior
Un enlace accionable junto al error.

## Actual behavior
Solo el texto del mensaje de la API nombra la ruta; no se tocó `expense-form` ni `features/purchases`. Está registrado como desviación en el TASK.

## Evidence
TASK, sección Implementación (desviaciones); el diff no incluye esos archivos. Requiere decidir: aceptar como deuda (cambio de Specification, aprobación del usuario) o implementar.
