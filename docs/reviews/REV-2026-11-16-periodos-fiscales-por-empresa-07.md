# REV-2026-11-16-periodos-fiscales-por-empresa-07: Claves i18n de otro feature para errores de nombre

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-16-periodos-fiscales-por-empresa.md (v1)
**Spec reference:** N/A
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Reutiliza CUSTOMERS.CUSTOMER_QUICK_CREATE.EL_NOMBRE_*; mismo patrón que la plantilla de referencia (deuda heredada).

## Expected behavior
Mover a COMMON en una tarea aparte.

## Actual behavior
Ver descripción.

## Evidence
Quality Gate (subagente aislado), period-dialog.component.html:17. Backend 1678 OK; frontend 1430 OK (2 de 3 corridas, ver nota del flake preexistente `screens-i18n.spec.ts:58-65`, ajeno al diff).
