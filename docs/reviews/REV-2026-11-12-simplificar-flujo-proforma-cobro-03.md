# REV-2026-11-12-simplificar-flujo-proforma-cobro-03: Mensaje de error engañoso cuando el monto supera el saldo

**Status:** Resolved (corregido el 2026-11-12; pendiente de reverificación en el segundo Quality Gate)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-12-simplificar-flujo-proforma-cobro.md (v1)
**Spec reference:** AC-05 (pago mayor al saldo), AC-15
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`validationError` en `payment-dialog.component.ts` usa la clave `RECEIVABLES.E_SUPERA_SALDO` («Una imputación supera el saldo del tratamiento.») tanto cuando una imputación manual excede el saldo de su tratamiento como cuando el monto total excede el saldo de la proforma.

## Expected behavior
Con el reparto automático, un monto mayor al saldo muestra un mensaje sobre el monto (p. ej. «El monto supera el saldo por cobrar»).

## Actual behavior
Al escribir 999 con saldo 150.00 aparece «Una imputación supera el saldo del tratamiento.», aunque la persona no está editando imputaciones y el reparto es automático.

## Evidence
Navegador, diálogo de cobro PRO-000002, monto «999»: `err: "Una imputación supera el saldo del tratamiento."`, «Confirmar cobro» deshabilitado (el bloqueo es correcto; solo el texto confunde).
