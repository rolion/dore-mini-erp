# REV-2026-10-30-reportes-adaptar-modulos-activos-05: AC-10: no se añadió la prueba de regresión que pedía el plan (paso 6)

**Status:** Open
**Severity:** Low
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-10-30-reportes-adaptar-modulos-activos.md (v1)
**Spec reference:** AC-10, INV-04, plan: Regression tests / paso 6
**Plan mode:** COMPLETO
**Suggested owner:** delivery-engineer

## Description
El plan (Integration tests y paso 6) pide un test en `reporting` que muestre que crear/pagar una compra no altera `expenses_total` ni `estimated_profit`. El TASK declara que no se añadió y que lo cubren tests de `purchases` (pagar/recibir no crea gastos). Esas pruebas verifican que no se crean gastos, no el resultado del dashboard; la desviación no está registrada como cambio de plan. Observación adicional: el permiso y `SourceAvailabilityAdapter` consultan `module_gate.enabled_keys` cada uno (2 consultas constantes por petición del dashboard, no N+1) mientras el plan/NFR dice una.

## Expected behavior
Un test de reporting con una compra confirmada/pagada que compruebe que dashboard y ganancia no cambian, o la desviación aprobada en el plan.

## Actual behavior
Sin test en `reporting` para AC-10; desviación solo mencionada en el TASK.

## Evidence
```
TASK-...md:89: AC-10 queda cubierto por purchases/tests/test_payment_api.py:144-155 y test_receipt_api.py:145-151 ...; no se añadió prueba nueva.
git diff origin/main...HEAD -- backend/modules/reporting/tests/test_api.py -> sin referencias a purchases
```
