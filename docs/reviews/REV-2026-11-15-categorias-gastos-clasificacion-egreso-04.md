# REV-2026-11-15-categorias-gastos-clasificacion-egreso-04: Faltan pruebas para edge cases y UI-02 del plan

**Status:** Resolved (verificado por el Quality Gate, 2.ª pasada)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-15-categorias-gastos-clasificacion-egreso.md (v1)
**Spec reference:** Test Specification; UI-02; edge cases
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Sin pruebas directas de: `accounting.services.describe_classifications`; reintento idempotente de pago tras cambiar la configuración; gasto anulado conserva instantánea; edición sin cambio de categoría; aserción de UI-02 (`data-testid=classification`); estado «Inactiva» de la pestaña; cobertura `accounting_disabled` explícita en la API de Gastos.

## Expected behavior
Cada regla y edge case del plan con su verificación.

## Actual behavior
La lógica es correcta al leer el código, pero no está fijada por pruebas.

## Evidence
Informe del Quality Gate (tabla AC → verificación).
