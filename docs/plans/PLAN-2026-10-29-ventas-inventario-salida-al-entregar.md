# PLAN-2026-10-29-ventas-inventario-salida-al-entregar (v1)

**Task:** TASK-ventas-inventario-salida-al-entregar · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** `docs/design/DDR-ventas-inventario-salida-al-entregar-dialogo-entrega-y-detalle.md` · `docs/adr/ADR-ventas-inventario-salida-al-entregar-orquestacion-y-contrato.md`

## Objective
Al pasar un pedido de Listo a Entregado, descontar atómicamente del almacén elegido las existencias de los productos que controlan stock, aplicando la política de stock negativo de la empresa, con trazabilidad visible desde el pedido y desde Inventario → Movimientos.

## Context
Ver TASK. PB-INV-004 (libro de movimientos, idempotencia) y PB-INV-007 (política) ya están en `main`; PB-CFG-003 no existe: se usa el almacén `is_default`.

# Specification

## Domain context
Bounded context principal: **Sales** (agregado `Order`, caso de uso `DeliverOrder`). Relacionado: **Inventory** (libro `StockMovement`, almacenes, política), **Catalog** (`tracks_stock`, unidad base), **Modularity** (política y habilitación).

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Pedido / entrega | `Order`; estados `NEW → IN_PREPARATION → READY → DELIVERED` (+ `CANCELLED`) | `sales/domain/order.py` |
| Ítem controlado | Línea cuyo producto tiene `tracks_stock=true` | catalog |
| Salida por venta | Movimiento `out` con origen `sales_order` | `inventory/domain/movement.py:36` |
| Referencia | `order_code` (P-XXXXXXXX), guardada en `reference` del movimiento | `sales/api/serializers.py:46` |
| Existencia / saldo | Σ entradas − Σ salidas del libro por producto y almacén | `GetBalance` |
| Saldo proyectado | Existencia − cantidad a entregar (informativo en el diálogo) | esta tarea |
Inconsistencia declarada: la historia habla de «referencia de salida»; no hay número de salida propio, se usa la referencia del pedido.

## Current behavior
`DeliverOrder` cambia estado/fecha sin tocar stock (`sales/application/commands.py:163-171`). El libro y la política están listos pero ningún productor de ventas los usa.

## Expected behavior
- `READY → DELIVERED` con Inventario habilitado e ítems controlados: se registra una salida por producto en el almacén elegido, el pedido pasa a Entregado, todo en una transacción.
- Sin ítems controlados o con Inventario deshabilitado: igual que hoy, sin almacén ni movimientos.
- El detalle del pedido muestra la salida; Movimientos muestra «Salida por venta» enlazada al pedido.

## Domain rules / invariants
- INV-01 (nueva): solo `READY → DELIVERED` genera salidas; ninguna otra acción (crear, preparar, listo, cobrar, editar) mueve stock ni reserva.
- INV-02 (nueva): pedido entregado y todas sus salidas se confirman juntos o ninguno (sin entrega parcial).
- INV-03 (nueva): un solo almacén por entrega, activo y de la empresa de la sesión.
- INV-04 (existente): la política de negativo la aplica Inventario bajo el bloqueo del almacén; Ventas no la reevalúa.
- INV-05 (nueva): identidad de origen `(sales_order, order.id, product_id)` + producto + almacén + tipo `out`; no admite un segundo descuento.
- INV-06 (existente): las cantidades son en unidad base, `Decimal`; la existencia sale del libro.
- INV-07 (existente): pedido entregado no se edita ni cancela (`OPEN_STATUSES`).

## Acceptance criteria
- **AC-01** Con 5 de un producto y entrega de 4: pedido `DELIVERED`, salida de 4, existencia 1.
- **AC-02** Con bloqueo y dos pedidos `READY` de 4 sobre saldo 5: solo una entrega se confirma; la otra responde 409 `insufficient_stock` (requested 4, available 1), permanece `READY` y no deja movimiento.
- **AC-03** Con negativos permitidos, ambas entregas se confirman; saldo −3; cada pedido tiene sus movimientos vinculados.
- **AC-04** Confirmar el mismo pedido varias veces (reintento, doble clic, concurrente) no duplica salidas ni descuenta dos veces.
- **AC-05** Si falla cualquier línea (validación u otra escritura) no se confirma el pedido ni ninguna salida; el pedido sigue `READY`.
- **AC-06** Un pedido con ítems controlados y no controlados genera movimientos solo para los controlados; sin controlados no se exige almacén ni se crean movimientos.
- **AC-07** El almacén es obligatorio si hay ítems controlados, debe existir en la empresa de la sesión y estar activo; un almacén de otra empresa o inactivo se rechaza (400) sin cambiar nada; sin almacén activo en la empresa → 409 `no_active_warehouse`.
- **AC-08** Con Inventario deshabilitado la entrega funciona como en el MVP (sin almacén ni movimientos); habilitarlo después no descuenta entregas anteriores.
- **AC-09** Crear, preparar, marcar listo y registrar cobro no cambian existencias.
- **AC-10** Si un producto aparece en varias líneas se suman sus cantidades para validar y se registra una salida por producto; cantidades en unidad base con la precisión del libro; la existencia de Existencias coincide con las salidas.
- **AC-11** `GET delivery-preview` informa por línea producto, cantidad, unidad, existencia, saldo proyectado e insuficiencia, política y almacenes activos; no escribe nada; solo del pedido de la empresa de la sesión.
- **AC-12** `stock_output` del pedido y `GET /api/stock-movements/?source_type=sales_order&source_id=` muestran referencia, almacén, fecha, producto, cantidad, unidad y usuario; el movimiento enlaza al pedido (`source.available`).
- **AC-13** Un pedido entregado no admite edición de ítems ni cancelación.
- **AC-14** UI del diálogo: precarga de almacén, tabla, avisos de bloqueo/negativo/sin almacén, deshabilitado durante el envío, datos conservados ante error, 409 actualiza la tabla y mantiene el diálogo.
- **AC-15** Aislamiento: dos empresas con mismos nombres de producto/almacén no se afectan; ninguna referencia de otra empresa se acepta.

## Edge cases / Error cases
- EDGE-01: otra pestaña ya entregó el pedido → 409 `invalid_transition`; la UI recarga.
- EDGE-02: el saldo cambia entre el preview y la confirmación → manda el servidor (409 con valores vigentes).
- EDGE-03: el almacén se desactiva entre preview y confirmación → 400 «El almacén está inactivo».
- EDGE-04: el producto dejó de controlar stock tras crear el pedido → no genera salida (se evalúa al entregar).
- EDGE-05: fecha de entrega inválida (futura/anterior al pedido) → 400 como hoy; no hay salidas.
- EDGE-06: cantidad con fracciones en producto sin fracciones → imposible por pedido entero; la validación de Inventario se mantiene.
- EDGE-07: pedido entregado cuando Inventario se deshabilita después → `stock_output` no se muestra mientras esté deshabilitado.

## Authorization / permissions
Sin roles nuevos: administrador de la empresa; API de Ventas requiere Ventas habilitado (`required_modules=('sales',)`) y la fachada de Inventario solo se usa con Inventario habilitado. Movimientos requiere Inventario habilitado; el enlace al pedido depende de Ventas habilitado. La empresa sale siempre de `shared/tenancy`.

## API contract
- **API-01** `GET /api/orders/<id>/delivery-preview/?warehouse_id=` → 200 `{inventory_enabled, requires_stock_output, allow_negative_stock, warehouses:[{id,name,is_default}], warehouse_id, lines:[{product:{id,name}, quantity, unit:{abbreviation}, available, projected, insufficient}]}`; 404 si no existe o es de otra empresa; 409 `invalid_transition` si no está `READY`; 400 si `warehouse_id` es inválido.
- **API-02** `POST /api/orders/<id>/deliver/` body `{delivered_date?, warehouse_id?}`: 200 pedido (como hoy) con `stock_output`; 400 `warehouse_id`; 409 `insufficient_stock {warehouse, lines:[{product,unit,requested,available}]}`; 409 `no_active_warehouse`; 409 `invalid_transition`. Retrocompatible: sin `warehouse_id` y sin ítems controlados responde igual que hoy.
- **API-03** `GET /api/orders/<id>/` incluye `stock_output` (`null` o `{reference, warehouse, occurred_at, movements[]}`).
- **API-04** `GET /api/stock-movements/` acepta `source_id` (uuid/texto del origen) combinado con `source_type`; valor inválido → 400.

## UI behavior
- **UI-01** Acción «Marcar como entregado» solo con la transición permitida; con ítems controlados abre el diálogo (DDR); si no, SweetAlert actual.
- **UI-02** Diálogo: referencia, fecha, almacén (select o texto), tabla Producto/Cantidad/Unidad/Existencia/Saldo proyectado.
- **UI-03** Avisos: bloqueo (`alert-danger`, confirmar deshabilitado, sin atajos), negativos permitidos (`alert-warning`), sin almacén activo (`alert-warning` con instrucción).
- **UI-04** «Confirmar entrega» con estado de envío; «Cancelar» cierra sin cambios; datos conservados al fallar.
- **UI-05** Tarjeta «Salida de inventario» en el detalle entregado + «Ver movimientos».
- **UI-06** Movimientos: «Salida por venta», chip de filtro por pedido, enlace al pedido.
Plantillas: detalle y lista con filtros (design-system sección 5).

## Non-functional requirements
Operación atómica y serializada por almacén; una consulta de saldos por llamada (no N+1); sin nuevas dependencias; mensajes en español; accesibilidad (`role=alert`, no solo color, foco en el diálogo).

## Out of scope
Reservas, descuento al cobrar/crear, entregas parciales, varios almacenes, conversiones de unidad, devoluciones/anulaciones, excepciones de negativo por operación, PB-CFG-003, recálculo retroactivo, número de salida propio.

## Open questions
- Cuando exista PB-CFG-003, el predeterminado configurado reemplazará al `is_default` en la preselección (cambio localizado en el preview).

# Test Specification

## Unit tests
- Sales application (fakes de `StockOutput`): `DeliverOrder` sin Inventario / sin ítems controlados / con ítems; orden de llamadas (deliver antes de la salida); propagación de errores sin guardar; agregación por producto; `warehouse_id` requerido (AC-05, AC-06, AC-07, AC-08, AC-10).
- Inventory application: `RecordOutputs` — todas las líneas validadas antes de insertar, lista completa de faltantes, política permitida/bloqueada, idempotencia por línea, cantidad distinta → `source_operation_mismatch` (AC-02, AC-03, AC-04, AC-05).
- Frontend: servicio (mapeo del preview, `deliver` con `warehouse_id`, 409 con `lines`), diálogo (precarga, avisos, deshabilitado, conserva datos, actualiza ante 409), detalle de pedido (flujo diálogo vs Swal, tarjeta de salida), lista de Movimientos (etiqueta, chip `source_id`) (AC-12, AC-14).

## Integration tests
- Django `TestCase` con Inventario real (API): AC-01, AC-03, AC-04 (doble POST), AC-05 (falla una línea con varios productos → nada), AC-06, AC-07 (otra empresa, inactivo, sin almacén), AC-08, AC-09, AC-10, AC-11, AC-12, AC-13, AC-15.
- Concurrencia en PostgreSQL (`TransactionTestCase` con hilos, como en PB-INV-007): AC-02 (dos pedidos sobre un mismo producto/almacén) y AC-04 (dos entregas del mismo pedido).
- `test_boundaries.py`: `sales → inventory` permitido solo desde `adapters.py` y por `services`.

## E2E
**NO** — no hay Playwright en el proyecto (instalarlo requiere confirmación y dependencia nueva). Los flujos se cubren con integración de API y specs de componente; la evidencia manual (UI + API) se documenta en `docs/tests/MANUAL-ventas-inventario-salida-al-entregar.md`.

## Regression tests
Suites existentes de Ventas (`test_api`, `test_application`, `test_services`), Inventario (movimientos, política, ajustes) y los specs de `order-detail`, `orders-api.service`, `movement-list`, `movement-detail`.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | Integración API (5 → 4 → saldo 1) |
| AC-02 | Integración + concurrencia PostgreSQL + unit `RecordOutputs` |
| AC-03 | Integración (saldo −3, movimientos por pedido) |
| AC-04 | Integración (reintento) + concurrencia PostgreSQL |
| AC-05 | Integración (2 productos, el segundo insuficiente) + unit `DeliverOrder` con fallo del puerto |
| AC-06 | Integración + unit `DeliverOrder` |
| AC-07 | Integración (400 otra empresa/inactivo/falta; 409 sin almacén) |
| AC-08 | Integración (módulo apagado; encender luego no descuenta) |
| AC-09 | Integración (transiciones previas y pago, saldo intacto) |
| AC-10 | Unit agregación + integración (precisión/unidad, Existencias = salidas) |
| AC-11 | Integración del preview (sin escritura, otra empresa 404) |
| AC-12 | Integración (`stock_output`, filtro `source_id`) + specs de Movimientos |
| AC-13 | Integración (editar/cancelar entregado → 409) |
| AC-14 | Specs de diálogo y detalle + guía manual |
| AC-15 | Integración con dos empresas |

# Implementation Plan

## Architecture considerations
Sales orquesta y Inventario ejecuta (ADR). Dominio `Order` intacto salvo exponer `code`. Un solo bloqueo de almacén por entrega; orden pedido → almacén. Sin migraciones.

## Proposed solution
1. **Inventory (backend)**: caso de uso `RecordOutputs` en lote; `InsufficientStock` con soporte de varias líneas; funciones de fachada nuevas `record_outputs`, `list_active_warehouses`, `get_balances`, `allow_negative_stock`, `list_movements_for_source`; filtro `source_id`; serializador 409 con `lines`.
2. **Sales (backend)**: puerto `StockOutput`/`InventoryAvailability` y adaptador; `DeliverOrder` extendido (actor y almacén); caso de uso de preview; vistas/serializers (`warehouse_id`, `delivery-preview`, `stock_output`); `Order.code`.
3. **Frontend**: servicio de pedidos (preview, deliver con almacén, `stockOutput`), `delivery-dialog`, cambios en `order-detail`, tarjeta de salida, etiqueta/filtro en Movimientos.
4. **Docs**: `ddd.md`, `modulos-implementados.md`, guía manual.

## Files/components affected
- Backend inventory: `application/movement_use_cases.py`, `application/movement_ports.py`, `domain/exceptions.py`, `services.py`, `api/insufficient_stock.py`, `api/movement_filters.py`, `domain/repositories.py` (`MovementFilters.source_id`), `infrastructure/django/movement_repository.py`, tests nuevos.
- Backend sales: `application/ports.py`, `application/commands.py`, `application/queries.py` (preview), `domain/order.py` (`code`), `infrastructure/adapters.py`, `api/views.py`, `api/serializers.py`, `api/urls.py`, `tests/test_boundaries.py` y tests nuevos.
- Frontend sales: `models/order.ts`, `services/orders-api.service.ts`, `components/delivery-dialog/*`, `components/stock-output-card/*`, `pages/order-detail/*`, `testing/order-fixtures.ts` y specs.
- Frontend inventory: `models/movement.ts`, `pages/movement-list/*`, `pages/movement-detail/*`, `services/movements-api.service.ts` y specs.
- Docs: `docs/architecture/ddd.md`, `docs/producto/modulos-implementados.md`, `docs/tests/MANUAL-ventas-inventario-salida-al-entregar.md`.

## Implementation steps
1. Inventory: `RecordOutputs` + `InsufficientStock` multilínea + fachada (lectura y escritura) + tests (INV-02..05, AC-02..05).
2. Inventory: filtro `source_id` y 409 con `lines` (API-04, AC-12).
3. Sales: puerto/adaptador, `DeliverOrder` con almacén y actor, `Order.code`, actualizar `test_boundaries.py` (INV-01..05, AC-01, 05..08, 10).
4. Sales: `delivery-preview` y `stock_output` en el detalle (API-01, API-03, AC-11, AC-12).
5. Sales API: contrato de `deliver` y errores (API-02, AC-07, AC-13, AC-15) + integración y concurrencia.
6. Frontend servicio y modelos (preview, deliver, `stockOutput`).
7. Frontend `delivery-dialog` y flujo en `order-detail` (UI-01..04, AC-14).
8. Frontend tarjeta de salida y movimientos (etiqueta, chip, enlace) (UI-05, UI-06).
9. Docs (`ddd.md`, módulos implementados, guía manual con evidencia) y corrida completa de pruebas.

## Database / migrations
Ninguna. La salida se lee del libro por origen; no se agregan columnas a `sales_order`.

## Risks
- Concurrencia solo verificable con PostgreSQL (la suite local debe correrse contra él).
- Saldos del diálogo desactualizados (mitigado: 409 con valores vigentes).
- Fallos preexistentes en la suite frontend: comparar contra la línea base.
- Cambio en `InsufficientStock` (varias líneas) debe mantener el contrato del 409 de ajustes y apertura.

## New dependencies
Ninguna.
