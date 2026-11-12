# REV-2026-11-12-simplificar-flujo-proforma-cobro-01: El diálogo de cobro no se cierra tras un pago exitoso y queda con datos obsoletos

**Status:** Resolved (corregido y reverificado en la ronda 2 del Quality Gate, 2026-11-12)
**Severity:** High
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-12-simplificar-flujo-proforma-cobro.md (v1)
**Spec reference:** AC-05, AC-06 («una sola confirmación… el éxito muestra el comprobante y refresca los importes»), AC-15 (foco al cerrar), UI-02
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
En `frontend/panel_admin/src/app/shared/components/payment-dialog/payment-dialog.component.ts`, el callback `next` de `confirm()` llama a `this.close()` y luego emite `paid`. `close()` empieza con `if (this.saving) return;`, pero `saving` sigue en `true` dentro de `next` (solo pasa a `false` en `finalize`, que corre después). Por tanto `close()` retorna sin cerrar el `<dialog>` ni devolver el foco al elemento que lo abrió. Las pruebas no lo detectan: ningún spec comprueba que el diálogo se cierre (o `opener.focus()`) tras un pago exitoso.

## Expected behavior
Tras un pago registrado el diálogo se cierra, el foco vuelve al botón que lo abrió (o a un destino válido) y la página muestra el comprobante con los importes refrescados.

## Actual behavior
El diálogo permanece abierto mostrando el saldo y el reparto anteriores al pago, con «Confirmar cobro» habilitado. El comprobante y los importes se actualizan solo detrás del diálogo modal. Si la persona vuelve a pulsar «Confirmar cobro», reenvía el mismo pago con la misma clave de idempotencia (el servidor lo reconoce como repetición: no se duplicó), pero la UI no lo explica. Ocurre en los tres puntos de entrada que usan `app-payment-dialog` (detalle de proforma genérica, ficha del paciente y, por el mismo componente, Cobros y proforma dental).

## Evidence
Navegador, usuario `revcobros`, proforma PRO-000002 (genérica), clic real en «Cobrar» → «Confirmar cobro»:
- Resultado leído por JS: `{"open":true, "dtext":"Registrar cobro · PRO-000002 ... Saldo por cobrar Bs 150.00 ...", "dls":"... Cobrado | Bs 300.00 | Saldo por cobrar | Bs 0.00"}` (diálogo abierto con saldo 150.00 cuando el saldo real ya era 0.00).
- Ficha del paciente (ODO-000001): tras pagar el 50 %, `{"open":true, ... "Cobrado Bs 150.00 ... Saldo Bs 150.00"}` y alerta «Pago registrado. Comprobante CB-000005 por Bs 150.00.» detrás del diálogo abierto.
- Un segundo clic en «Confirmar» devolvió el mismo comprobante CB-000003 (un solo pago de 150.00 en el servidor).
- Causa: `payment-dialog.component.ts`, `close()`: `if (this.saving) return;` invocado desde `next` antes de `finalize`.
