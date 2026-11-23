# TASK-pedido-pantalla-unica-creacion: Crear el pedido en una sola pantalla

**Etapa actual:** REVIEW
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
Ver `docs/plans/PLAN-2026-11-23-pedido-pantalla-unica-creacion.md` (v2, COMPLETO). Specification readiness: READY.

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

**Deuda técnica.** `StockOutputAdapter` lanza `InsufficientStockForDelivery` también al iniciar preparación (el nombre dice «entrega»); se dejó para no ampliar el alcance. Un reintento tras un 201 perdido podría duplicar el pedido (riesgo aceptado en el ADR).

## Review
**Resultado: sin PASS.** El revisor devolvió FAIL condicional: no hay hallazgos Critical ni High y ningún test falla por el diff, pero no se ejecutó la suite contra PostgreSQL ni la revisión visual, y no se declara PASS con verificaciones aplicables sin ejecutar.

- [REV-01](docs/reviews/REV-2026-11-23-pedido-pantalla-unica-creacion-01.md) (Low, IMPLEMENTATION): Espacio perdido en urls.py (flake8 E231)
- [REV-02](docs/reviews/REV-2026-11-23-pedido-pantalla-unica-creacion-02.md) (Medium, IMPLEMENTATION): Suite backend contra PostgreSQL no ejecutada
- [REV-03](docs/reviews/REV-2026-11-23-pedido-pantalla-unica-creacion-03.md) (Low, SPECIFICATION): Falta el foco al selector de producto tras agregar (UI-05)
- [REV-04](docs/reviews/REV-2026-11-23-pedido-pantalla-unica-creacion-04.md) (Low, IMPLEMENTATION): Pruebas planificadas sin escribir
- [REV-05](docs/reviews/REV-2026-11-23-pedido-pantalla-unica-creacion-05.md) (Low, SPECIFICATION): Errores de `items` como lista de textos y no indexados (plan sin actualizar)
- [REV-06](docs/reviews/REV-2026-11-23-pedido-pantalla-unica-creacion-06.md) (Low, IMPLEMENTATION): Almacén guardado inactivo: la entrega y la vista previa se comportan distinto; nombre vacío
- [REV-07](docs/reviews/REV-2026-11-23-pedido-pantalla-unica-creacion-07.md) (Low, ARCHITECTURE): `placement.py` importa un helper privado de `commands.py`
- [REV-08](docs/reviews/REV-2026-11-23-pedido-pantalla-unica-creacion-08.md) (Low, DESIGN): Anchos fijos `style="width: …"` inline en la tabla
- [REV-09](docs/reviews/REV-2026-11-23-pedido-pantalla-unica-creacion-09.md) (Low, IMPLEMENTATION): Marca de fila con faltante por nombre y `toFieldErrors` frágil con `null`
Evidencia completa en la sección Testing del PR 118.

**Correcciones posteriores (2026-11-23, delivery-build):** REV-01, 04, 06 y 09 corregidos (ver su sección «Resolución»). Verificación propia: frontend 1794 de 1794 en verde, `npm run lint` e `i18n:check` limpios; backend `test_place_order`, `test_order_warehouse`, `test_api` y `test_delivery_inventory` (139) en verde solo sobre SQLite. REV-03 y REV-05 resueltos con el PLAN v2 (cambio de Specification aprobado por el usuario el 2026-11-23). Siguen abiertos REV-02 (PostgreSQL), REV-07 y REV-08 (Low) y la revisión visual.

## Publicación
_Pendiente_
