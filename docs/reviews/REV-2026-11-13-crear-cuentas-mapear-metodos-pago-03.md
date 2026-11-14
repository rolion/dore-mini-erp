# REV-2026-11-13-crear-cuentas-mapear-metodos-pago-03: Desactivar cuenta sin confirmación previa (UI-02)

**Status:** Resolved
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-13-crear-cuentas-mapear-metodos-pago.md (v1)
**Spec reference:** UI-02
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
UI-02 pide confirmación de desactivación con la lista de métodos afectados; `AccountsTabComponent.toggleActive` desactiva directo y muestra el 409 después. Desvío no declarado antes de este informe.

## Expected behavior
Diálogo de confirmación, o aceptar la desviación y ajustar UI-02 (cambio de Specification: requiere aprobación).

## Actual behavior
Ver descripción.

## Evidence
`accounts-tab.component.ts` `toggleActive`; el motivo 409 sí se muestra vía `blockReason` con los métodos.

## Resolution (2026-11-13)
`DeactivateDialogComponent` confirma antes de desactivar y lista los métodos activos que usan la cuenta (bloquea); specs de pestaña y diálogo.
