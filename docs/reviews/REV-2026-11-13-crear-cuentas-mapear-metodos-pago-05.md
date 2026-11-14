# REV-2026-11-13-crear-cuentas-mapear-metodos-pago-05: Menú de Contabilidad visible sin restricción de rol

**Status:** Open
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-13-crear-cuentas-mapear-metodos-pago.md (v1)
**Spec reference:** UI-01
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El ítem no tiene restricción de rol; hoy solo existe el rol admin, por lo que no hay impacto real. La API devuelve 403 a no admin.

## Expected behavior
Filtrar por rol si se añaden roles.

## Actual behavior
Ver descripción.

## Evidence
`visibleRoutes` solo distingue `personnel`.
