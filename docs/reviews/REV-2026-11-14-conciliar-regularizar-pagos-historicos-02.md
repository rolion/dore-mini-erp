# REV-2026-11-14-conciliar-regularizar-pagos-historicos-02: Función muerta `regularization_stamp`

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-14-conciliar-regularizar-pagos-historicos.md (v1)
**Spec reference:** N/A (CLAUDE.md: no agregar abstracciones sin necesidad)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`regularization_stamp` (domain/regularization.py:221) no se usa en ningún sitio.

## Expected behavior
Sin código muerto.

## Actual behavior
Función definida y sin referencias.

## Evidence
`grep -rn regularization_stamp backend` solo muestra su definición (la otra coincidencia es un nombre de prueba distinto).
