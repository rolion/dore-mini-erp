# ADR-ciclo-pedido-entrega-cobro-frontend-feature: Feature Angular `sales`, código compartido y relación con otras features

**Estado:** Propuesto
**Task relacionado:** TASK-ciclo-pedido-entrega-cobro
**Fecha:** 2026-10-08

## Contexto
Los DDR de este task definen lista, formulario, detalle (ítems, importes, pagos, acciones de estado), selector de cliente con creación rápida y conexión del historial en el perfil de cliente. `ddd.md:1011-1034` propone `features/sales/{pages/order-list|order-detail|order-create, components/order-form|order-items|order-status|payment-form, services/sales-api.service.ts, models/order.ts|payment.ts, sales.routes.ts}`. Existen `features/products` y `features/customers` con el mismo molde (`ADR-catalogo-productos-mvp-frontend-feature`, `ADR-clientes-mvp-frontend-feature`), y ese último dejó anotado extraer `Page<T>` y los estilos `btn-tbl-*` a `shared/` "cuando haya una tercera feature" (`docs/tasks/TASK-clientes-mvp.md`, deuda técnica): Sales es esa tercera feature. `frontend/panel_admin/src/app/shared/` no existe. `CLAUDE.md`: lógica no visual en servicios, tipos explícitos sin `any`, Reactive Forms, sin suscripciones colgadas. Dependencias de UI ya instaladas: `@ng-select/ng-select`, `@ng-bootstrap/ng-bootstrap`, `@swimlane/ngx-datatable`, `sweetalert2`, `ngx-toastr`.

## Decisión
- **Estructura:** `src/app/features/sales/` con `models/` (`order.ts`, `payment.ts`), `services/orders-api.service.ts`, `pages/{order-list,order-form,order-detail}`, `components/{order-status-badge,payment-status-badge,order-items,order-payments,order-summary}`, `testing/order-fixtures.ts`, `sales.routes.ts` y un `index.ts` (API pública de la feature). Ruta `sales/orders` en `app.routes.ts` con `loadChildren` (como `catalog/products`): `''` lista, `new` y `:id/edit` formulario, `:id` detalle (`new` antes de `:id`). Menú: entrada directa "Pedidos" en `assets/data/routes.json`, clave `MENUITEMS.ORDERS.TEXT` en `en/es/de`, ícono `shopping-cart`; `sidebar-menu.spec.ts` se actualiza.
- **Servicio:** `OrdersApiService` convierte DTO snake_case ↔ modelos tipados; errores 400 → errores por campo, 409 → `OrderRuleError { code, detail }`, 404 → error tipado. **Los importes son `string` en los modelos** (como los entrega el servidor) y solo se formatean para mostrarlos; el navegador **no suma, multiplica ni redondea** importes (los totales vienen del servidor).
- **Estado de pantalla:** el detalle conserva el pedido como estado de la página y lo reemplaza con la respuesta de cada mutación; las acciones visibles salen de `editable`, `allowed_transitions` y `can_register_payment` del servidor. Los filtros y la página de la lista viven en los query params de la URL (se conservan al volver del detalle). Sin suscripciones colgadas (`takeUntilDestroyed`/`async`).
- **Extracción a `shared/` (primer paso del plan, commit aparte):** crear `src/app/shared/models/page.ts` (`Page<T>`) y un parcial de estilos compartido con `btn-tbl-edit/view/update/toggle` y migrar `products` y `customers` a usarlos (cambio mecánico cubierto por sus specs existentes). Sales nace usando `shared/`. Solo esos dos elementos; no se crea una librería de componentes.
- **Relación entre features (sin ciclos):**
  - `sales → products` y `sales → customers` mediante el `index.ts` de cada feature (API pública): `ProductsApiService` para el selector de productos activos y `CustomersApiService` para el selector de clientes activos. No se importan `pages/` ni detalles internos.
  - Se agrega en `features/customers` el componente **`customer-quick-create`** (modal `NgbModal`, nombre y teléfono, reutiliza el diálogo de duplicado), exportado por su `index.ts` y consumido por el formulario de pedido. Es la última fase del plan y **separable**.
  - **`customers` no importa `sales`:** el historial del perfil se conecta con un servicio propio mínimo, `features/customers/services/customer-orders-api.service.ts`, que consume el contrato HTTP `GET /api/orders/?customer_id=` y alimenta `customer-purchase-history` (modelo `CustomerOrderSummary`, filas con enlace a `/sales/orders/:id`). Es el "método de servicio y binding" que previó el ADR de historial.
- **Pantallas:** siguen los DDR (`ngx-datatable` en lista con atajos y filtros; tablas Bootstrap para ítems y pagos; `ng-select` para cliente y producto; `input type="date"`; `Swal` para entregar y cancelar con motivo; formulario de pago inline). Sin dependencias nuevas.
- **Pruebas:** specs del servicio (mapeo de DTO y errores 400/409/404), de lista (atajos → query params), formulario, detalle (acciones según `allowed_transitions`; alertas "entregado con saldo" / "pagado pendiente de entrega" / "cancelado"), ítems, pagos y quick-create. La verificación se acota a los specs de las features tocadas, porque la suite completa tiene fallas preexistentes de la plantilla.

## Alternativas consideradas
- **Seguir duplicando `Page<T>` y estilos en Sales:** más rápido, pero llega a tres copias y rompe el umbral que el ADR de clientes fijó. Se extrae (mecánico y con specs existentes).
- **Librería compartida de componentes de tabla/lista:** sobreingeniería; solo hay dos elementos repetidos.
- **Importar `OrdersApiService` de Sales desde Customers para el historial:** crea un ciclo entre features (Sales ya usa componentes de Customers). Se usa un servicio mínimo propio del lado de Customers sobre el contrato HTTP.
- **Mover la creación rápida de cliente dentro de `features/sales`:** evita el borde entre features pero duplica el formulario y el diálogo de duplicado de Customers. Se mantiene en Customers, exportada por su API pública.
- **Un store global (NgRx):** el estado es local a cada página y se refresca con la respuesta del servidor; innecesario.
- **Calcular totales en el navegador para respuesta instantánea:** duplica reglas de dominio y arriesga divergencia con el servidor (REQ-SAL-005). Descartado.

## Estrategia de rollback / mitigación
Aditivo en su mayor parte (feature, ruta, entrada de menú, componente nuevo en Customers). El único cambio sobre código existente es la extracción a `shared/` y el servicio de historial en `customers`, ambos mecánicos y con specs. Rollback = revertir el PR; la extracción va en un commit separado para poder revertirla sin perder Sales. Sin feature flag: si el backend de pedidos no está disponible, las pantallas muestran el error de red por `toastr` y el resto de la app no se ve afectado.

## Consecuencias
- Queda fácil: una tercera feature con el mismo molde; el historial real del cliente con un cambio acotado; el frontend no replica reglas de negocio.
- Queda más difícil: mantener la regla de "APIs públicas por feature" por convención; el detalle del pedido concentra bastante lógica de UI (ítems, descuento, pagos, estados), por lo que se divide en componentes pequeños con entradas/salidas tipadas.
- Deuda aceptada: textos de pantallas solo en español (solo el menú se traduce); sin tablero de cobros ni acciones rápidas en la lista; importes mostrados con formato `Bs` implícito (sin moneda en el modelo).
