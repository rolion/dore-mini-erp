# REV-2026-10-27-bloquear-api-modulos-deshabilitados-07: Con módulos en caché desactualizados, la búsqueda opcional de clientes sigue expulsando de Pedidos

**Status:** Accepted (limitación conocida: ventana estrecha con módulos desactualizados; ver Known limitations del PR)
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-10-27-bloquear-api-modulos-deshabilitados.md (v2, UI-05)
**Spec reference:** AC-04, AC-10, UI-05, DDR integraciones opcionales
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start (decidir si se acepta como limitación o se acota el interceptor)

## Description
UI-05 evita pedir clientes solo si `ModulesService.isDisabled('customers')` es verdadero, es decir, si el cliente ya cargó la configuración. Si otro administrador deshabilita Clientes mientras la sesión actual tiene la caché anterior (o los módulos aún no se cargaron: `isDisabled` es falso con `null`), `CustomerOptionsService.search` pide `/api/customers/`, recibe 403 `module_disabled` y `errorInterceptor` navega a «Módulo no habilitado (Clientes)» aunque la persona está en Pedidos (habilitado). Esto es el mismo mecanismo de REV-01, acotado a una ventana de desfase.

## Expected behavior
Una petición opcional rechazada por una integración ausente no debería sacar a la persona de un módulo habilitado.

## Actual behavior
La navegación ocurre una vez; tras ella `loadQuietly()` refresca el menú y la siguiente visita a Pedidos ya no pide clientes. Es una ventana estrecha y se autocorrige, pero la expulsión sigue siendo posible.

## Evidence
Lectura de código: `core/interceptor/error.interceptor.ts` (navega ante cualquier `module_disabled`), `core/service/modules.service.ts` (`isDisabled`), `sales/services/customer-options.service.ts`. El plan v2 lo deja sin cubrir. No ejecutado en navegador. Opciones: no navegar cuando el módulo rechazado no coincide con el de la ruta activa, o aceptarlo documentado como limitación.
