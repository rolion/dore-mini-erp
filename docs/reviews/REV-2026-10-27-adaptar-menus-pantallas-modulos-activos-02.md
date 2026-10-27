# REV-2026-10-27-adaptar-menus-pantallas-modulos-activos-02: Con Clientes deshabilitado, el detalle de pedido sigue enlazando al cliente

**Status:** Resolved
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-27-adaptar-menus-pantallas-modulos-activos.md (v1)
**Spec reference:** AC-06 y requerimiento PB-MOD-003 AC (3): «los paneles no muestran errores por módulos ausentes»; DDR de PB-MOD-002 (integraciones opcionales)
**Plan mode:** COMPACTO
**Suggested owner:** delivery-engineer

## Description
`frontend/panel_admin/src/app/features/sales/pages/order-detail/order-detail.component.html:107-108` muestra el cliente del pedido como enlace `[routerLink]="['/pocketbiz/customers', customer.id]"` sin consultar los módulos. Un pedido puede tener cliente (se creó con Clientes habilitado) y después Clientes puede apagarse (independiente de Ventas).

## Expected behavior
Con Clientes deshabilitado el detalle de pedido muestra el nombre del cliente como texto (el nombre ya viene en la respuesta de Ventas), sin enlace a una pantalla no disponible.

## Actual behavior
El enlace sigue visible; al pulsarlo, `moduleGuard` lleva a «Módulo no habilitado» desde una pantalla de un módulo activo, en un flujo normal. No hay petición a la API de Clientes (no es un 403), y la pantalla de error es clara y permite volver; por eso Medium y no High.

## Evidence
Lectura de código (no verificado en navegador): el HTML citado; `app.routes.ts` protege `customers` con `moduleGuard`. Resto de enlaces entre módulos revisados sin hallazgo: `customer-purchase-history` (cubierto por `*appIfModule="'sales'"`), `reports.component.html:138` (dentro de `*appIfModule="'customers'"`), `dashboard.component.html` (Reportes exige Ventas y Gastos), formularios de pedido y filtros de lista (cliente oculto y sin petición con Clientes apagado).
