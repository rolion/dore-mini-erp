# REV-2026-10-27-bloquear-api-modulos-deshabilitados-01: El interceptor 403 expulsa de Pedidos y Reportes cuando Clientes está deshabilitado

**Status:** Open
**Severity:** High
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-10-27-bloquear-api-modulos-deshabilitados.md (v1)
**Spec reference:** AC-07, AC-08, AC-10, UI-03 (y DDR: «el error se propaga para que ninguna lista lo muestre como sin resultados»)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-engineer (con delivery-ui-design si cambia el flujo)

## Description
`errorInterceptor` trata cualquier 403 `module_disabled` navegando a `/module-disabled`, sin distinguir si la petición era del módulo de la pantalla actual o una integración opcional. Con Clientes deshabilitado (estado alcanzable desde PB-MOD-001), dos pantallas de módulos que SÍ siguen habilitados lanzan peticiones a Clientes:
- Lista de pedidos: `order-list.component.ts:111,116` llama a `CustomerOptionsService.search('')` al iniciar, que consulta `GET /api/customers/` (403 `module_disabled`). El `catchError` de `customer-options.service.ts` traga el error, pero el interceptor ya navegó.
- Formulario de pedido: `order-form.component.ts:153` hace la misma búsqueda.
- Reportes: `reports.component.ts:48` carga `reports/top-customers/` (403 `customers`).

## Expected behavior
AC-07/AC-08 y el objetivo del plan: «Ventas y Reportes siguen funcionando sin Clientes». La pantalla «Módulo no habilitado» debe aparecer al abrir un módulo deshabilitado, no al usar un módulo habilitado.

## Actual behavior
Al abrir Pedidos o Reportes con Clientes deshabilitado, la primera petición a Clientes dispara la navegación a «Módulo no habilitado (Clientes)»: ambas pantallas quedan inutilizables desde la UI (la API funciona, la UI no). Antes de este PR esa combinación funcionaba. El plan deja «ocultar tarjetas/campos por módulo» a PB-MOD-003, pero el interceptor convierte esa omisión en una expulsión, no en una tarjeta vacía.

## Evidence
Lectura de código (no verificado en navegador): `frontend/panel_admin/src/app/core/interceptor/error.interceptor.ts` (`disabledModule` + `router.navigate([MODULE_DISABLED_ROUTE]...)` sin condición), `features/sales/pages/order-list/order-list.component.ts:111-116`, `features/sales/services/customer-options.service.ts`, `features/reporting/pages/reports/reports.component.ts:48`. Las specs de `interceptors.spec.ts` solo cubren el 403 de la propia ruta. Opciones: navegar solo si el módulo rechazado coincide con el de la ruta activa (`route.data.module`) o actualizar el menú sin navegar para integraciones opcionales; y evitar la carga de clientes/top-clientes cuando el módulo no está habilitado (o adelantar lo necesario de PB-MOD-003).
