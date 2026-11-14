# REV-2026-11-14-conciliar-regularizar-pagos-historicos-01: «Existente» no compara documento ni comprobante (ADR decisión 5)

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-14-conciliar-regularizar-pagos-historicos.md (v1)
**Spec reference:** INV-06 / ADR decisión 5 («entrada idéntica en monto, fecha, método, moneda y documento»)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`classify` en `backend/modules/accounting/domain/regularization.py` solo compara amount, payment_date, method y currency contra la entrada existente. El ADR menciona también el documento (`origin_document_ref`).

## Expected behavior
Una entrada con otro `origin_document_ref` se informaría como diferencia, o el ADR/plan aclara que el documento no se compara.

## Actual behavior
Una entrada con documento distinto se clasifica como `existing`. INV-06 y AC-07 solo exigen importe/fecha/método/moneda, así que no incumple la Specification; es una discrepancia ADR vs. código.

## Evidence
Lectura de `classify()` (tupla de comparación de 4 campos). Ninguna prueba cubre documento distinto.
