# REV-2026-11-17-reconocer-compras-mercaderia-deuda-proveedores-08: El reparto deuda/anticipo cuenta recepciones sin asiento como deuda reconocida (límite no documentado)

**Status:** Open
**Severity:** Low
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-11-17-reconocer-compras-mercaderia-deuda-proveedores.md (v2)
**Spec reference:** INV-06, INV-08, ADR pagos y anticipos §3 y §10; Edge cases
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
`split_for_payment` usa `Purchase.received_value` (todas las recepciones confirmadas) como deuda reconocida. Una recepción sin asiento (anterior al corte, en un hueco, o previa al despliegue de esta tarea) forma parte de ese valor aunque el libro nunca acreditó Cuentas por pagar por ella. Un pago posterior con cobertura registra la parte «deuda» como Debe Cuentas por pagar sin crédito previo (saldo deudor), y no como anticipo. INV-08 habla de «valor recibido reconocido». El ADR §10 documenta solo el caso inverso (pago anterior al corte) y «recepciones históricas no se regularizan»; no dice qué pasa con pagos nuevos sobre ellas. En la práctica es el comportamiento razonable (la regularización es CONT-07), pero conviene dejarlo escrito y aceptado.

## Expected behavior
La Specification/ADR indica explícitamente el efecto (saldo deudor en Cuentas por pagar por pagos con cobertura de recepciones sin asiento) o define otra regla.

## Actual behavior
Efecto no documentado; el invariante INV-08 en el texto no coincide literalmente con la implementación.

## Evidence
```
backend/modules/purchases/application/payment_commands.py (split_for_payment):
    value = purchase.received_value(receipts.received_totals(purchase.id))
    paid = payments.debt_paid_total(purchase.id) + receipts.advance_applied_total(purchase.id)
backend/modules/purchases/application/receipt_commands.py (_recognized_amount) sí limita lo reconocido a recepciones con asiento.
```
Verificación de conservación (prueba aleatoria de 25 semillas: recibir/pagar/revertir, comparando libro y columnas) pasó; esto es solo la brecha documental.
