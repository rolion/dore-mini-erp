# REV-2026-11-24-crm-listado-clientes-01: Última compra se muestra en ISO y no dd/MM/yyyy

**Status:** Closed (corregido en e0b9dc49; verificado en segunda pasada del Quality Gate)
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-24-crm-listado-clientes.md (v1)
**Spec reference:** UI-01, design-system §7/§8
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
La columna y la tarjeta de «Última compra» imprimen `lastPurchaseAt` tal como llega (`YYYY-MM-DD`).

## Expected behavior
Fechas con formato `dd/MM/yyyy` (design-system §8; el resto del producto usa `| date: 'dd/MM/yyyy'`).

## Actual behavior
Se muestra por ejemplo 2026-11-10.

## Evidence
frontend/panel_admin/src/app/features/crm/pages/crm-customer-list/crm-customer-list.component.html: `{{ row.lastPurchaseAt || ('CRM.CUSTOMER_LIST.NO_PURCHASES' | translate) }}` (líneas de tabla y de tarjeta, sin pipe date). Referencia correcta: features/customers/pages/customer-detail/customer-detail.component.html:82 `{{ s.lastPurchaseDate | date: 'dd/MM/yyyy' }}`.
