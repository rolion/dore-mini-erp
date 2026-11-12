# REV-2026-11-12-simplificar-flujo-proforma-cobro-05: El foco queda en `body` cuando el cobro liquida el saldo y el botón que abrió el diálogo desaparece

**Status:** Resolved (corregido el 2026-11-12 y cubierto por prueba de componente; sin reverificar en navegador)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-12-simplificar-flujo-proforma-cobro.md (v1)
**Spec reference:** AC-15 (foco al cerrar el diálogo), REV-01 («el foco vuelve al botón que lo abrió o a un destino válido»)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`PaymentDialogComponent.dismiss()` hace `this.opener?.focus()`. Cuando el pago deja el saldo en 0, la página oculta el botón que abrió el diálogo («Registrar pago» en Cobros, «Cobrar» en la proforma o la fila de la ficha) y `focus()` sobre un elemento ya desconectado no tiene efecto: el foco pasa a `body`.

## Expected behavior
Si el opener ya no existe, el foco se mueve a un destino válido (p. ej. el comprobante/alerta de éxito o el encabezado de la página).

## Actual behavior
En Cobros, tras pagar el saldo completo (Bs 75.00 de ODO-000001), el diálogo se cierra, el comprobante aparece y los importes se actualizan, pero `document.activeElement` es `BODY`. Con pagos parciales el foco sí vuelve al botón (verificado en proforma genérica, ficha del paciente y Cobros).

## Evidence
Navegador, `revcobros`, Cobros ODO-000001: `{"open":false,"focus":"BODY ...","openerConnected":false,"alert":["Pago registrado. Comprobante CB-000008 por Bs 75.00."], "payBtn": false}`. Con pago parcial (PRO-000001, 75.00 de 150.00): `open:false`, foco en el botón «Cobrar».
