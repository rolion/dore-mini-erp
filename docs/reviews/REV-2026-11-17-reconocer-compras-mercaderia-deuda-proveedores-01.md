# REV-2026-11-17-reconocer-compras-mercaderia-deuda-proveedores-01: Deriva de centavos en el reconocimiento tras revertir una recepción que no es la última

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-17-reconocer-compras-mercaderia-deuda-proveedores.md (v1)
**Spec reference:** INV-01 (recibir todo reconoce el total de la compra), AC-02 (la suma de recepciones = total)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`Purchase.receipt_amount` valora cada recepción como diferencia del subtotal acumulado usando `received_before` = recibido de recepciones confirmadas. Si se revierte una recepción intermedia (su asiento se revierte completo) y luego se recibe el resto, el acumulado `received_before` ya no coincide con el que se usó al reconocer las recepciones restantes, y la suma de los asientos netos deja de igualar el subtotal de la línea.

## Expected behavior
Tras recibir todo, el saldo reconocido (Haber Proveedores neto) es igual al total de la compra.

## Actual behavior
Línea 0,3 x 0,15 (subtotal 0,05). Recepciones A=0,1 (importe 0,02), B=0,1 con before=0,1 (0,01). Se revierte A. Se recibe C=0,2 con before=0,1: 0,05 - 0,02 = 0,03... el neto queda B+C = 0,04 frente a un total de 0,05 (deriva de 0,01).

## Evidence
```
compute_subtotal(0.1,0.15)=0.02  (0.2)=0.03  (0.3)=0.05
B = sub(0.2)-sub(0.1) = 0.01 ; C(before=0.1, qty 0.2) = sub(0.3)-sub(0.1) = 0.03 ; neto B+C = 0.04 vs total 0.05
```
(razonamiento verificado con el cálculo del dominio; no hay prueba que cubra reversión intermedia + re-recepción). Solo con precios/cantidades fraccionarios que redondean; impacto de 1 centavo, escenario raro.

## Resolution
Resuelto: `Purchase.receipt_amount` valora contra los asientos vigentes (`recognized_totals` del puerto); pruebas de dominio, comandos e integración.
