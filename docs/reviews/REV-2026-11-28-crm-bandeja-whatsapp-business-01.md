# REV-2026-11-28-crm-bandeja-whatsapp-business-01: Dos pruebas Karma del menú lateral fallan por la nueva entrada «Bandeja»

**Status:** Resolved (pendiente de re-verificación por el Quality Gate)
**Severity:** High
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-28-crm-bandeja-whatsapp-business.md (v1)
**Spec reference:** PLAN AC-11 / Regression tests (suites existentes verdes); UI-01
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
La entrada CRM → Bandeja (assets/data/routes.json) se añadió sin actualizar frontend/panel_admin/src/app/layout/sidebar/sidebar-menu.spec.ts, que fija la lista exacta de rutas del submenú CRM y el total de títulos (55).

## Expected behavior
La suite Karma completa pasa: el spec del menú refleja el submenú CRM con /pocketbiz/crm/inbox y el nuevo total de títulos.

## Actual behavior
2 pruebas fallan; el archivo sidebar-menu.spec.ts no está en el diff (git diff origin/crm...HEAD --name-only | grep -c sidebar-menu → 0).

## Evidence
`npx ng test --watch=false --browsers=ChromeHeadless` → `TOTAL: 2 FAILED, 2004 SUCCESS` (2006 ejecutadas).
- "Sidebar menu (routes.json) has a translation in en, es and pt for every menu title (AC-09) FAILED — Expected 56 to be 55. (sidebar-menu.spec.ts:110)"
- "Sidebar menu (routes.json) has the business menu, Dentistry, Purchases, Inventory and Settings > Modules FAILED — Expected $.length = 6 to equal 5. Unexpected $[5] = '/pocketbiz/crm/inbox' in array. (sidebar-menu.spec.ts:22)"
El TASK declara solo "28 pruebas Karma de la bandeja OK": no se ejecutó la suite completa.


## Resolution
Menú: `sidebar-menu.spec.ts` actualizado (Bandeja, 56 títulos).
