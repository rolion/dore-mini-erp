# REV-2026-11-24-crm-listado-clientes-04: HEX de respaldo en el SCSS de CRM

**Status:** Open
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-24-crm-listado-clientes.md (v1)
**Spec reference:** design-system §8 (sin HEX propios)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El SCSS declara `var(--bs-border-color, #dee2e6)` y `var(--bs-secondary-color, #6c757d)` con HEX de respaldo.

## Expected behavior
Usar solo las variables del tema, sin HEX sueltos.

## Actual behavior
Dos HEX literales en features/crm (los valores de respaldo coinciden con Bootstrap, impacto visual nulo).

## Evidence
frontend/panel_admin/src/app/features/crm/pages/crm-customer-list/crm-customer-list.component.scss: `border: 1px solid var(--bs-border-color, #dee2e6);` y `color: var(--bs-secondary-color, #6c757d);`
