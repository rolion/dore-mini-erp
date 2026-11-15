# REV-2026-11-15-conciliar-regularizar-pagos-historicos-03: Estados «cargando»/error de carga de la pantalla y EDGE-02 sin prueba

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-14-conciliar-regularizar-pagos-historicos.md (v2)
**Spec reference:** AC-17, UI-05, EDGE-02, Test Specification (ningún AC sin prueba)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
AC-17/UI-05 piden estados cargando, vacío, error de validación/servidor y 409. El componente tiene `loadingSetup`/`setupError` (carga de métodos y cuentas) pero `regularization.component.spec.ts` no los ejercita (solo vacío, validación, 409, REV-03/04). En backend, EDGE-02 (empresa sin pagos/faltantes → informe vacío, exit 0) no tiene una prueba propia.

## Expected behavior
Una prueba por estado declarado (cargando y error de carga en el componente; informe vacío con exit 0 en el comando).

## Actual behavior
Ramas sin prueba: `ngOnInit` con error (`setupError`) y el `@if (loadingSetup)`; comando sobre una empresa sin pagos.

## Evidence
- `grep -n "loading\|setupError" regularization.component.spec.ts` → sin coincidencias.
- Nombres de pruebas de `test_regularization.py`: ninguna cubre empresa sin pagos.

## Resolución
Specs nuevas: estado cargando y error de carga de la pantalla (`loading`, `setup-error`) y, en backend, `test_company_without_payments_reports_empty_and_exits_cleanly` (EDGE-02: informe vacío, exit 0, sin escribir).
