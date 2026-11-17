# REV-2026-11-17-contabilizar-ventas-cobros-sin-duplicar-01: Cobro previo a la cobertura y confirmación posterior duplican el camino

**Status:** Resolved (PLAN v2, opción A aprobada por la persona)
**Severity:** Medium
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-11-17-contabilizar-ventas-cobros-sin-duplicar.md (v1)
**Spec reference:** EDGE-02 / INV-02
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
Un pedido NEW cobrado cuando Contabilidad aún no cubría la fecha (libro anterior) y confirmado después con cobertura reconoce el total completo; ese cobro previo nunca acredita Cuentas por cobrar.

## Expected behavior
Un cobro nunca debe quedar en ambos caminos para el mismo importe (tarjeta, AC de camino único).

## Actual behavior
Ingresos no se duplican, pero Cuentas por cobrar queda sobrestimada. La Specification solo cubre pedidos confirmados antes de la cobertura. Requiere decisión de negocio (bloquear reconocer pedidos con cobros previos, reconocer solo el saldo, o documentar el límite); un cambio de Specification exige aprobación.

## Evidence
`adapters.py` `SalesPostingAdapter.record_payment` / `recognize`; sin prueba en `test_sales_posting.py`. Hallado por el Quality Gate (subagente aislado, 2026-11-17); suite backend 1986 OK y frontend 1574 OK.
