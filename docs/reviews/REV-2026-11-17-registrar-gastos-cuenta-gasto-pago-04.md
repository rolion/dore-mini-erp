# REV-2026-11-17-registrar-gastos-cuenta-gasto-pago-04: La clave de idempotencia del formulario no se renueva: tras editar datos y reintentar un alta ya aceptada queda en 409 sin salida

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-17-registrar-gastos-cuenta-gasto-pago.md (v1)
**Spec reference:** AC-04, UI-01
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`ExpenseFormComponent.idempotencyKey` se genera una sola vez por componente. Si una peticion tuvo exito pero la respuesta se perdio y la persona modifica datos y reenvia, recibe 409 `idempotency_key_reused` y solo puede recargar la pagina.

## Expected behavior
Ante `idempotency_key_reused` el formulario ofrece una salida clara (o renueva la clave cuando los datos cambian).

## Actual behavior
El 409 se muestra como alerta (`postingError`) sin accion posible.

## Evidence
- `frontend/panel_admin/src/app/features/expenses/pages/expense-form/expense-form.component.ts` (`private readonly idempotencyKey = crypto.randomUUID()`, `showServerError`).
