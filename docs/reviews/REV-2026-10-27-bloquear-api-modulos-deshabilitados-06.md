# REV-2026-10-27-bloquear-api-modulos-deshabilitados-06: URL de pedidos con filtro `customer` y Clientes deshabilitado deja un filtro oculto y la lista con error

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-27-bloquear-api-modulos-deshabilitados.md (v2, UI-05)
**Spec reference:** UI-05, EDGE-02 (cliente no asignable con Clientes deshabilitado)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-engineer

## Description
`parseState` (`order-list-filters.ts:121-127`) toma `?customer=<id>` de la URL (marcadores, enlaces previos) sin considerar el módulo. Con Clientes deshabilitado el selector está oculto pero el filtro sigue activo y se envía `customer_id`; el backend responde 400 (`OrderListCreateView.get`, `customer_id: 'El módulo Clientes no está habilitado.'`).

## Expected behavior
Con Clientes deshabilitado la lista ignora el filtro de cliente (o lo descarta de la URL) y muestra los pedidos.

## Actual behavior
La lista muestra el toast genérico de validación, no carga filas (`catchError` → `EMPTY`) y el filtro causante no es visible; solo «Limpiar filtros» lo resuelve. No hay expulsión ni pérdida de datos.

## Evidence
Lectura de código: `order-list.component.ts:143-155,159-170`, `order-list-filters.ts:86,121-127`, `backend/modules/sales/api/views.py` (rama `CUSTOMERS_DISABLED`). Sin spec para este caso. No ejecutado en navegador.
