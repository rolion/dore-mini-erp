# REV-2026-10-27-bloquear-api-modulos-deshabilitados-05: Editar un pedido con Clientes deshabilitado desvincula el cliente en silencio

**Status:** Resolved
**Severity:** High
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-27-bloquear-api-modulos-deshabilitados.md (v2, UI-05)
**Spec reference:** AC-11 (los datos se conservan mientras el módulo está deshabilitado), AC-07, UI-05
**Plan mode:** COMPLETO
**Suggested owner:** delivery-engineer

## Description
Con Clientes deshabilitado la API devuelve `customer: null` para los pedidos vinculados (decisión 1 del usuario) y la UI oculta el selector (UI-05). Pero `OrderFormComponent.onSubmit()` siempre arma `customerId: value.customer?.id ?? null`, y en edición el control `customer` se rellena con `order.customer` (que llega `null`). `OrdersApiService` envía `customer_id` cuando `input.customerId !== undefined` (también `null`). El backend (`UpdateOrder` omite la validación si `customer_id is None`; `Order.update_details` asigna `self.customer_id = customer_id`) borra el vínculo.

## Expected behavior
Con Clientes deshabilitado, editar cualquier campo de un pedido (notas, canal, fechas) no debe tocar `customer_id`: el vínculo se conserva y reaparece al rehabilitar Clientes (AC-11).

## Actual behavior
Basta abrir la edición de un pedido vinculado y guardar (p. ej. cambiar las notas) para que `customer_id` quede en NULL de forma permanente; al rehabilitar Clientes el pedido ya no tiene cliente. Pérdida silenciosa de datos de negocio causada por una acción rutinaria. Ninguna spec lo cubre (las specs de UI-05 solo comprueban que el selector no se muestra y que no se piden clientes).

## Evidence
Lectura de código: `frontend/panel_admin/src/app/features/sales/pages/order-form/order-form.component.ts:125` (`customerId: value.customer?.id ?? null`) y `:170` (`customer: order.customer`); `features/sales/services/orders-api.service.ts:156`; `backend/modules/sales/application/commands.py:69-72`; `backend/modules/sales/domain/order.py:203-204`. No ejecutado en navegador. Corrección sugerida: con `customersDisabled` omitir `customerId` del payload en edición (y añadir spec de formulario más un test de API que compruebe que un PATCH sin `customer_id` conserva el vínculo con Clientes deshabilitado).
