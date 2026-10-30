# REV-2026-10-30-compras-registrar-pagos-saldo-02: El diálogo no recarga el saldo tras un rechazo por saldo desactualizado

**Status:** Fixed
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-30-compras-registrar-pagos-saldo.md (v1)
**Spec reference:** DDR «Errores» («Si el saldo cambió por otro pago, el mensaje indica el saldo vigente y se recarga el resumen»); EDGE-03; AC-18
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Cuando otro pago reduce el saldo mientras el diálogo está abierto y el servidor responde 400 por sobrepago, el diálogo conserva lo escrito y muestra el saldo vigente en el mensaje (correcto), pero no vuelve a leer la compra: sigue mostrando «Saldo actual: Bs 100.00» y el resumen de la pestaña de fondo queda desactualizado; «Pagar el saldo completo» rellenaría de nuevo el saldo viejo y volvería a fallar.

## Expected behavior
El DDR indica que se recarga el resumen cuando el saldo cambió, de modo que el saldo mostrado y el botón «Pagar el saldo completo» usen el saldo vigente.

## Actual behavior
Mensaje del servidor correcto, pero el saldo del encabezado del diálogo y el resumen de la pestaña no se refrescan hasta cerrar y volver a abrir tras recargar la página.

## Evidence
Prueba visual (escritorio): compra de Bs 100.00; se abrió el diálogo, se registró por API un pago de Bs 30.00 y se envió Bs 80 desde el diálogo. Resultado: texto rojo «El monto no puede superar el saldo pendiente (70.00).» bajo el monto, con el formulario intacto, pero el encabezado seguía en «Saldo actual: Bs 100.00» y el campo «Saldo: Bs 100.00». Tras cancelar, la pestaña seguía en Total pagado Bs 0.00 / Saldo Bs 100.00 hasta recargar la página. Ningún spec del diálogo cubre este refresco.

## Resolución
Corregido: tras un 400/409 el diálogo relee la compra (`PurchasesApiService.get`), muestra el saldo vigente, emite `purchaseRefreshed` y la pestaña recarga lista y detalle sin cerrar el diálogo ni borrar lo escrito. Pruebas en `payment-dialog` y `purchase-payments-tab`. No se repitió la prueba visual en navegador de este flujo.
