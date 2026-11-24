# TASK-pedido-pantalla-unica-creacion: Crear el pedido en una sola pantalla

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-pedido-pantalla-unica-creacion
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/118

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-23 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-11-23 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | Veredicto NEEDS_ARCHITECTURE; decisiones de negocio respondidas por la persona (almacén, estado NEW) | delivery-start |
| 2026-11-23 | PLANNING → ENGINEERING | Specification READY; PR abierto | delivery-start |
| 2026-11-23 | ENGINEERING → REVIEW | Implementación completa; pruebas propias en verde (backend solo con SQLite) | delivery-build |
| 2026-11-23 | REVIEW (sin PASS) | Quality Gate: sin Critical/High; faltan PostgreSQL y revisión visual; 9 REV abiertos | delivery-publish |
| 2026-11-23 | REVIEW → PUBLISH | Segundo Quality Gate: PASS (2387 backend con PostgreSQL, 1811 frontend); 2 hallazgos Low abiertos | delivery-publish |
| 2026-11-23 | PUBLISH | Tercer Quality Gate sobre c557ff45: PASS (2387 backend, 1813 frontend, lint, i18n, build); REV-12 Low (documentos desactualizados) abierto | delivery-publish |
| 2026-11-23 | PUBLISH (corrección) | REV-10 y REV-11 corregidos; PLAN v4 (Specification aprobada por el usuario) | delivery-build |

## Investigación

### Requerimiento
Tal como se recibió: hoy un pedido se crea en 2 pantallas (datos y luego detalle). Debe haber **una sola pantalla de creación** en el estado NEW con:

- Fila 1: Cliente (combobox) · Canal de venta (combobox).
- Fila 2: Fecha del pedido (date picker) · Fecha de entrega (date picker).
- Fila 3: Almacén (combobox).
- «Detalle del pedido»: Producto (combobox) · Cantidad (input) · botón Agregar; debajo, tabla Producto · Precio unitario · Cantidad · Subtotal.
- Pie a la derecha: Subtotal (suma de subtotales), Descuento (no mayor al permitido en la configuración de Ventas), Total (subtotal − descuento) y botón **Iniciar preparación**, que **crea el pedido ya en estado IN_PREPARATION**.

Decisiones de la persona (respondidas en esta sesión):
1. **Almacén: guardar y validar stock.** El pedido guarda el almacén; al iniciar preparación se valida el stock de cada producto controlado en ese almacén; la entrega usa ese almacén por defecto y el diálogo de entrega puede cambiarlo.
2. **Estado NEW: se conserva solo para lo existente.** La pantalla nueva no genera pedidos NEW; los NEW existentes siguen abriéndose y editándose en el detalle. Sin migración de datos.

### Hechos encontrados
- `frontend/panel_admin/src/app/features/sales/sales.routes.ts:9-11` — `new` y `:id/edit` usan `OrderFormComponent`; `:id` usa `OrderDetailComponent`.
- `.../pages/order-form/order-form.component.ts:36-52,126-158` — el formulario solo captura cliente, canal, fechas y notas; al guardar hace `POST /api/orders/` y navega al detalle (`:149-151`). No tiene productos, descuento ni almacén.
- `.../pages/order-detail/order-detail.component.ts:204-220` — los productos y el descuento se agregan en el detalle, una llamada por acción (`addItem`, `applyDiscount`), y `prepare` (`:162`) confirma el pedido.
- `.../components/order-items/order-items.component.ts:43-47,121-128` — buscador de productos (activos, vendibles, `salePrice`), cantidad entera ≥ 1; emite eventos y no calcula importes.
- `.../components/order-summary/order-summary.component.ts:7-35` — el descuento se envía al servidor; el navegador no calcula.
- `.../services/orders-api.service.ts:275-324` — endpoints existentes (`create`, `addItem`, `applyDiscount`, `prepare`, `deliver`, `deliveryPreview`).
- `.../services/sales-settings.service.ts:19-44` — expone solo canal y método de pago predeterminados; **no** expone `sales.max_discount_percent`.
- `backend/modules/sales/application/commands.py:50-74` — `CreateOrder` crea el pedido en NEW sin ítems; `:102-129` `AddOrderItem` toma nombre y precio vigentes del catálogo (el cliente nunca envía el precio); `:158-173` `ApplyOrderDiscount` aplica el tope `max_discount_percent`; `:176-185` `StartOrderPreparation`.
- `backend/modules/sales/domain/order.py:197-208` — `Order.create` (estado inicial NEW, `:187`); `:276-286` `add_item` (rechaza producto duplicado); `:306-316` `apply_discount` (tope en % del subtotal, `max_percent` por empresa); `:320-325` `start_preparation` (exige ≥ 1 ítem).
- `backend/modules/modularity/domain/settings.py:51` — ajuste `sales.max_discount_percent` («Descuento máximo (% del subtotal)»), entre 0 y 100; leído por `SalesSettingsAdapter` (`backend/modules/sales/infrastructure/adapters.py:93-106`).
- `backend/modules/sales/application/commands.py:198-239` — `DeliverOrder` valida y descuenta stock **solo al entregar**; exige `warehouse_id` si hay productos controlados; `controlled_lines` (`application/delivery.py:35-42`) y el puerto `StockOutput` (`application/ports.py:96-114`) ya ofrecen productos controlados, almacenes activos, saldos y política de stock negativo.
- `backend/modules/sales/application/delivery.py:45-53` — `suggested_warehouse` propone el único almacén activo o el predeterminado.
- `backend/modules/sales/api/views.py:161-177` — `POST /api/orders/` valida con `OrderInputSerializer` y ejecuta `CreateOrder`.
- `backend/modules/sales/migrations/` — 0001 a 0003; la próxima es `0004`.
- `docs/design/design-system.md:158-160` — plantilla «Variante de un solo paso con totales calculados» (`features/purchases/pages/purchase-form`): cabecera + tabla de líneas, subtotal por línea y total de solo lectura calculados con una función pura de aritmética entera que replica la regla del servidor; tras guardar manda el servidor.
- `docs/adr/ADR-ciclo-pedido-entrega-cobro-*.md` y `docs/design/DDR-ciclo-pedido-entrega-cobro-formulario-y-detalle-pedido.md` — decisiones vigentes del ciclo del pedido (formulario de datos + detalle con ítems).

### Hipótesis / supuestos no confirmados
- El cliente sigue siendo **opcional** (venta de mostrador), como hoy.
- Se conserva el campo **Notas** (opcional) aunque el boceto no lo muestre, para no perder capacidad existente.
- Con Inventario deshabilitado no se muestra el combobox de Almacén; con Clientes deshabilitado no se muestra el de Cliente (comportamiento actual).
- El precio mostrado en la tabla es el vigente al agregar; el servidor toma el precio vigente al crear (puede diferir si cambió entre ambos instantes; manda el servidor).

### Módulos y dependencias relacionadas
Sales (dominio, aplicación, API, infraestructura) como contexto principal. Catalog (precio y estado del producto, vía `ProductCatalog`), Customers (validación de cliente) e Inventory (almacenes, saldos y stock negativo, vía `StockOutput` → fachada `services.py`). Modularity (ajuste de descuento máximo).

### Implementaciones similares existentes
`features/purchases/pages/purchase-form` (cabecera + líneas + total calculado, un solo paso); `features/inventory/pages/stock-opening` (formulario con líneas); `DeliverOrder` / `PreviewOrderDelivery` (validación de stock por almacén).

### Comportamiento actual
Crear un pedido = 1) formulario de datos → `POST /api/orders/` (NEW); 2) detalle: agregar productos uno a uno, aplicar descuento, `prepare`. El stock y el almacén no intervienen hasta la entrega.

### Restricciones
`CLAUDE.md`: dinero en `Decimal`; no editar migraciones aplicadas; aislamiento por `company_id`; el dominio no importa Django; estados cambian por métodos del agregado; módulos no se importan infraestructura entre sí; textos solo con claves i18n en es/en/pt; Reactive Forms; sin `any`.

### Riesgos identificados
- Contrato API nuevo y un campo nuevo en la tabla de pedidos (migración aditiva y nullable).
- El stock se valida al iniciar preparación **sin reservarlo**: puede faltar al entregar; la entrega sigue revalidando.
- Reintento de red tras un 201 perdido podría duplicar el pedido (sin clave de idempotencia). Mitigación en la UI: botón deshabilitado mientras envía.
- Cálculo de importes duplicado en el navegador (informativo); el servidor es la autoridad.
- Un pedido NEW existente conserva `warehouse_id` nulo: la entrega sigue pidiéndolo.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — cambia el contrato API del pedido (creación atómica), agrega un campo persistido (migración) y toca la frontera Sales ↔ Inventory (validación de stock al iniciar preparación) más Catalog y Customers.

### Diseño requerido
**SI** — reemplaza el flujo de dos pantallas por una pantalla de formulario con líneas y totales.

## Diseño
Ver `docs/design/DDR-pedido-pantalla-unica-creacion-formulario-unico.md`.

## Arquitectura
Ver `docs/adr/ADR-pedido-pantalla-unica-creacion-creacion-atomica.md`.

## Plan
Ver `docs/plans/PLAN-2026-11-23-pedido-pantalla-unica-creacion.md` (v4, COMPLETO). Specification readiness: READY.

## Implementación

**Resumen.** `POST /api/orders/start/` crea el pedido completo (cabecera, productos, descuento y almacén) en una sola transacción y lo deja en `IN_PREPARATION`; la ruta `/pocketbiz/sales/orders/new` es ahora una pantalla única (`order-create`) que arma el borrador en el navegador y llama a ese endpoint con «Iniciar preparación».

**Backend** (commit `feat(...): POST /api/orders/start/`)
- Dominio: `Order.warehouse_id` y `Order.assign_warehouse()` (INV-07). Migración aditiva `sales/0004_order_warehouse` (nullable, sin FK).
- `PlaceOrder` (`sales/application/placement.py`): valida cabecera, cliente, líneas (activo, vendible, entero, sin repetir), descuento con el tope de Ventas, almacén y existencia en el almacén vía el puerto `StockOutput`; todo o nada (INV-01..06, AC-04..06, 09, 10).
- API: `OrderStartView`, `OrderStartSerializer`, `warehouse {id, name}` en la salida del pedido (API-01/02).
- Entrega: `DeliverOrder` y `PreviewOrderDelivery` usan el almacén guardado como valor por defecto (API-03, AC-07).
- Pruebas: `sales/tests/test_place_order.py` (18 casos) y `DETAIL_KEYS` de `test_api.py` con `warehouse`.

**Frontend**
- `order-create` (página, plantilla y spec), `order-amounts.ts` (importes en centavos con `bigint`), `OrdersApiService.start`, `warehouse` en el modelo, `maxDiscountPercent` en `SalesSettingsService`, almacén en el detalle, ruta `new` con `unsavedChangesGuard`, claves `SALES.ORDER_CREATE.*` en es/en/pt y export público de `WarehousesApiService` en `features/inventory/index.ts`.
- Pantalla de referencia seguida: variante «un solo paso con totales calculados» (`purchase-form`). Reutiliza `MoneyPipe`, `ng-select` y el alta rápida de cliente de `order-form`. `design-system.md` ahora cita `order-create` como segunda referencia.

**Desviaciones respecto al plan**
- Los errores de líneas de `items` se devuelven como una lista de textos «Línea N: …» (no como estructura indexada): la UI los muestra tal cual.
- `delivery-dialog` no se modificó: ya preselecciona `preview.warehouseId`, y ahora el servidor propone el almacén del pedido (AC-07 queda cubierto por la API y su prueba).
- Se conservó el campo opcional «Notas» (supuesto del TASK).

**Verificación propia (no es el Quality Gate)**
- Backend: `test_place_order` (18) en verde. La suite completa de `modules.sales` solo corrió con SQLite (no hay credenciales de PostgreSQL en esta máquina): 63 errores son de `pg_advisory_xact_lock`/`pg_locks`, propios de PostgreSQL; **falta correr la suite con PostgreSQL** en `delivery-publish`.
- Frontend: `npm run lint` limpio, `npm run i18n:check` sin faltantes y 1790 pruebas de Karma en verde.
- `ruff`/`flake8`: cero avisos en lo nuevo (el repositorio conserva avisos previos en `views.py`, `commands.py`, `order.py` y `mappers.py`).

**Ampliación (2026-11-23, pedida por el usuario en el mismo PR): nuevo detalle del pedido en preparación, listo y entregado** (PLAN v3, AC-11..AC-15; DDR `detalle-pedido-en-curso`).
- `order-detail` usa la vista de consulta para `IN_PREPARATION`, `READY` y `DELIVERED` (cabecera con código y badges, acciones a la derecha, datos en cuatro columnas, productos, importes y pagos de solo lectura); `NEW` y `CANCELLED` conservan el detalle anterior.
- Nuevo `PaymentDialogComponent` (modal de «Registrar pago»); `OrderPaymentsComponent` gana `readonly`.
- Pruebas: specs nuevos de `payment-dialog` y del detalle en curso; se adaptaron 3 pruebas del detalle anterior. Frontend 1811 de 1811, lint, `i18n:check` y `ng build` en verde.
- Efecto a tener presente: un pedido confirmado ya no se edita desde la interfaz (productos, descuento y «Editar datos»); la API sigue permitiéndolo. Revisión visual en navegador: ver el párrafo siguiente.

**Revisión visual en navegador (2026-11-23, hecha por quien implementó; no sustituye al Quality Gate):** backend y frontend levantados con una base SQLite descartable y datos de prueba. Verificado en escritorio (1440 px) y móvil (375 px, sin scroll horizontal) y con el tema oscuro de la plantilla:
- Pantalla `/sales/orders/new`: estructura pedida, producto + cantidad + «Agregar», totales (Subtotal 155, Descuento 5, Total 150) y creación real en `IN_PREPARATION` con almacén, que navega al detalle.
- Detalle en preparación, listo y entregado: cabecera con badges y acciones, datos en cuatro columnas, productos, importes y pagos; «Marcar listo» cambió el estado a «Listo» y el botón a «Marcar entregado»; el modal de pago mostró el error de monto (999 > saldo) sin perder lo escrito y registró 120.00 (tag «Pagado», sin botón de pago); el entregado muestra entrega real y salida de inventario.
- Hallazgo bajo, ya existente: en el tema oscuro el título `Pedido P-…` (un `h4` fuera de tarjeta) queda en negro sobre fondo oscuro; es un límite de la plantilla y no se tocó.
- No verificado: el tope de descuento configurado (la base de prueba usa 100 %; cubierto por pruebas automáticas) y la tabla de líneas de `order-create` en móvil.

**Deuda técnica.** REV-07 (`placement.py` importa `_customer_errors` de `commands.py`) y REV-08 (anchos `style="width"` inline en la tabla de `order-create`, igual que `order-items`). `StockOutputAdapter` lanza `InsufficientStockForDelivery` también al iniciar preparación (el nombre dice «entrega»); se dejó para no ampliar el alcance. Un reintento tras un 201 perdido podría duplicar el pedido (riesgo aceptado en el ADR).

## Review
**Resultado: PASS** (segundo Quality Gate, subagente independiente sobre PLAN v3, 58 archivos). Sin hallazgos Critical ni High. Primera revisión: FAIL condicional por falta de PostgreSQL; sus hallazgos están cerrados (01, 02, 03, 04, 05, 06, 09) o aceptados como deuda técnica (07, 08).

- Backend (PostgreSQL, serie): `Ran 2387 tests in 405.860s` → `OK`. `ruff`/`flake8`: 0 avisos nuevos sobre las 453 líneas añadidas; `bandit`: 0 hallazgos.
- Frontend: `npm run lint` limpio, `i18n:check` (2470 claves, 0 faltantes), `ng test` 1811 de 1811, `npm run build` sin errores; `npm audit`: 2 moderadas en `hono` (dependencia ajena al diff).
- AC-01..AC-15, INV-01..07, API-01..04 y UI-01..06: todos con verificación real.
- Hallazgos nuevos (Low, abiertos, no bloquean):
- [REV-10](docs/reviews/REV-2026-11-23-pedido-pantalla-unica-creacion-10.md) (Low, DESIGN, abierto): Sin saldo visible en el detalle de consulta (preparación y listo)
- [REV-11](docs/reviews/REV-2026-11-23-pedido-pantalla-unica-creacion-11.md) (Low, IMPLEMENTATION, abierto): Sin prueba de la recarga tras `stale` del modal de pago
- **Corrección posterior al Quality Gate:** REV-10 (Pagado y Saldo en los importes, PLAN v4 aprobado por el usuario) y REV-11 (prueba de la recarga tras `stale`) corregidos; frontend 1813 de 1813, lint e `i18n:check` en verde. Tercer Quality Gate (subagente independiente) sobre este cambio: PASS; backend 2387 de 2387 con PostgreSQL, frontend 1813 de 1813, lint, `i18n:check` y build en verde. Hallazgo nuevo: REV-12 (Low, documentación desactualizada tras PLAN v4). Revisión visual de las filas Pagado/Saldo en navegador: no verificada.
- Limitación: el revisor independiente no verificó la app en navegador; la revisión visual propia de quien implementó (escritorio, móvil y tema oscuro) consta en `## Implementación`.

## Publicación
PR 118 listo para aprobación humana; **no se mergea desde el flujo**. Cambios sensibles que requieren decisión humana: una **migración de base de datos** (`sales/0004_order_warehouse`, aditiva y nullable) y un cambio de contrato API (endpoint nuevo `POST /api/orders/start/`, ADR `creacion-atomica`). Rollback: ver el ADR (columna nullable sin uso al revertir el código).
