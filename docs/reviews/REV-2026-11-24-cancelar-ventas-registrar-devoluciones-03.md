# REV-2026-11-24-cancelar-ventas-registrar-devoluciones-03: Checklist de design-system §8: HEX nuevos, fechas ISO sin formatear y enlaces «Ver» ambiguos

**Status:** Resolved parcialmente (fecha con pipe y aria-label corregidos; HEX copiados del patrón existente de `askCancelReason` y formato de moneda sin cambio)
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-24-cancelar-ventas-registrar-devoluciones.md (v1)
**Spec reference:** UI-01, UI-03, UI-04; design-system §7 y §8
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Revisión estática (la app no se levantó) de `return-dialog` y `order-reversal-card` contra la checklist §8.

## Expected behavior
Sin HEX nuevos; fechas `dd/MM/yyyy`; enlaces con nombre accesible distinguible.

## Actual behavior
1. `order-detail.component.ts` `confirmRefund` añade `confirmButtonColor: '#dc3545'` y `cancelButtonColor: '#fb7823'` (HEX escritos a mano; copiados del patrón de `askCancelReason`, pero son líneas nuevas).
2. `return-dialog.component.html`: `{{ payment.paymentDate }}` muestra la fecha ISO `AAAA-MM-DD` sin `date` pipe (el resto de la UI usa `dd/MM/yyyy`).
3. `order-reversal-card.component.html`: todos los enlaces a movimientos y asientos tienen el texto «Ver» (y el reverso, «Ver» o la referencia) sin `aria-label` que incluya producto/evento; un lector de pantalla oye N enlaces idénticos.
4. `confirmRefund` interpola `order.paidTotal` como texto crudo (`'20.00'`) en vez del pipe/formato `money` («Bs»).
Positivo: textos con `translate`/`tr()`, `<label for>` en motivo y casilla, `scope="col"`, `role="alert"` en el error, botones deshabilitados durante `saving`, `aria-label` en cerrar.

## Evidence
```
$ git diff origin/main...HEAD -- order-detail.component.ts | grep -n "dc3545\|fb7823"
+      confirmButtonColor: '#dc3545',
+      cancelButtonColor: '#fb7823',
$ grep -n "paymentDate" return-dialog.component.html
<li data-testid="payment-line">{{ payment.paymentDate }} · {{ payment.amount | money }}</li>
```
Verificación visual (claro/oscuro, 390/1440 px): NO REALIZADA.
