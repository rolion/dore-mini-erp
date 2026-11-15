# REV-2026-11-15-modularidad-corte-historicos-contabilidad-03

Status: Open
Severity: Low
Category: DESIGN
Related plan: docs/plans/PLAN-2026-11-15-modularidad-corte-historicos-contabilidad.md
Spec reference: UI-02; design-system.md sección 8 (usar money y componentes compartidos)
Plan mode: COMPLETO
Suggested owner: delivery-build

## Description
La columna 'Apertura' de la tabla de cuentas muestra account.openingBalance como cadena cruda, sin el pipe money ni la moneda de la cuenta.

## Expected behavior
Importe formateado con el pipe/componente compartido de moneda (con la moneda de la cuenta).

## Actual behavior
Se renderiza el valor tal cual llega de la API (p. ej. 250.00).

## Evidence
frontend/panel_admin/src/app/features/accounting/components/accounts-tab/accounts-tab.component.html (<td> con {{ account.openingBalance }}); existe shared/pipes/money.pipe.ts. Revisión visual no verificada (no se levantó la app).

## Resolución
Resuelto: la columna «Apertura» usa el pipe `money` para cuentas BOB y muestra importe + moneda para las demás. Spec: `shows the opening balance formatted as money…` en `accounts-tab.component.spec.ts`.
