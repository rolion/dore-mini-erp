# REV-2026-10-27-adaptar-menus-pantallas-modulos-activos-01: Con Ventas deshabilitado y Clientes habilitado, abrir un cliente lleva a «Módulo no habilitado»

**Status:** Resolved
**Severity:** High
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-27-adaptar-menus-pantallas-modulos-activos.md (v1)
**Spec reference:** AC-06 y requerimiento PB-MOD-003 AC (3): «los paneles no muestran errores por módulos ausentes»; regla del DDR de PB-MOD-002 «una pantalla de un módulo habilitado no pide datos de una integración opcional deshabilitada»
**Plan mode:** COMPACTO
**Suggested owner:** delivery-engineer

## Description
El detalle de cliente (`/pocketbiz/customers/:id`) pide siempre el historial de pedidos del cliente a `GET /api/orders/?customer=...` (módulo Ventas). Clientes no depende de Ventas (`MODULE_CATALOG`: `customers` sin `requires`), y Ventas puede apagarse una vez apagado Reportes (que lo requiere). Esa combinación es una configuración válida de empresa (solo Catálogo, Clientes, Gastos).

## Expected behavior
Con Clientes habilitado y Ventas deshabilitado, el detalle de cliente se muestra completo, sin la sección de historial de compras (o sin pedirla), y sin pantalla de error.

## Actual behavior
`CustomerDetailComponent.loadOrders` llama a `CustomerOrdersApiService.list` sin consultar los módulos. La API responde 403 `module_disabled` (módulo `sales`) y `errorInterceptor` ejecuta `router.navigate([MODULE_DISABLED_ROUTE], ...)`, de modo que al abrir cualquier cliente la persona es expulsada a «Módulo no habilitado» desde una pantalla de un módulo activo. Este PR añadió `*appIfModule` justamente para este patrón pero no revisó este caso (solo Clientes dentro de Ventas/Reportes).

## Evidence
Lectura de código (no verificado en navegador):
- `frontend/panel_admin/src/app/features/customers/pages/customer-detail/customer-detail.component.ts` (`loadOrders` tras cargar el cliente) y `.../services/customer-orders-api.service.ts:34` (`${environment.apiUrl}/orders/`).
- `frontend/panel_admin/src/app/core/interceptor/error.interceptor.ts:38-41` (403 `module_disabled` -> navega a la pantalla de error).
- `backend/modules/modularity/domain/modules.py` (`customers` sin `requires`; `reporting` requiere `sales`).
- Plantilla `customer-purchase-history.component.html:24` enlaza además a `/pocketbiz/sales/orders/:id`.
