# TASK-ventas-inventario-salida-al-entregar: Conectar Ventas con Inventario y generar salidas al entregar (PB-INT-002)

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-ventas-inventario-salida-al-entregar
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/27

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-29 | (nuevo) → INVESTIGATION | Task creado desde `main` al día (incluye PB-INV-007, PR #26) | delivery-start |
| 2026-10-29 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | Nueva dependencia sales → inventory, contrato API nuevo y atomicidad entre módulos | delivery-start |
| 2026-10-29 | PLANNING → ENGINEERING | Specification READY (sin decisiones de negocio abiertas; ver Plan) | delivery-start |

## Investigación

### Requerimiento
**PB-INT-002 · Conectar Ventas con Inventario y generar salidas al entregar** (Integraciones, P1). Como administrador, quiero que entregar un pedido genere automáticamente la salida de los productos que controlan stock para que las existencias reflejen las entregas sin registrar movimientos a mano.

Resumen del texto recibido (completo en el mensaje de origen; los AC se trasladan al PLAN):
- La salida ocurre **solo** en la transición válida `READY → DELIVERED`. Crear, preparar, marcar listo o cobrar no descuenta ni reserva.
- Con Inventario habilitado: movimientos solo para productos con `tracks_stock`. Con Inventario deshabilitado: el flujo actual, sin almacén.
- Ventas → Pedidos (`/sales/orders`): «Marcar como entregado» abre un diálogo (referencia, un solo almacén activo, tabla producto / cantidad / unidad base / existencia / saldo proyectado) si hay ítems controlados; si no, la confirmación habitual.
- Política de stock insuficiente (PB-INV-007): bloqueo → rechazo completo con producto, almacén, solicitado y existente; permitido → aviso del saldo proyectado y se confirma.
- Atomicidad y serialización por producto/almacén; idempotencia por identidad de origen; el pedido muestra la salida y «Ver movimientos»; Inventario → Movimientos muestra «Salida por venta» con enlace al pedido.
- Fuera de alcance: reservas, descuento al cobrar, entregas parciales, varios almacenes, conversiones de unidad, devoluciones/anulaciones, excepciones de negativo por operación.

### Hechos encontrados
- `backend/modules/sales/application/commands.py:163-171` — `DeliverOrder` solo llama `order.deliver(...)` y guarda; no conoce Inventario. Es el punto de integración.
- `backend/modules/sales/domain/order.py:311-319` — `Order.deliver` exige `READY`, valida la fecha y fija `DELIVERED`. `:363-365` — solo los estados abiertos (`NEW/IN_PREPARATION/READY`) son editables y `:321-323` solo ellos se cancelan: un pedido entregado ya no se edita ni cancela.
- `backend/modules/sales/domain/order.py:259-261` — un producto aparece una sola vez por pedido (`duplicate_product`); `sales/infrastructure/django/models.py:52-55` lo refuerza con `UniqueConstraint(order, product_id)`. La agregación por producto que pide la historia es defensiva.
- `backend/modules/sales/infrastructure/django/models.py:40-48` — `quantity` es `PositiveIntegerField` (enteros); el pedido no guarda almacén ni referencia de salida.
- `backend/modules/sales/api/views.py:72-90` — `_run` envuelve toda mutación en `transaction.atomic()`; el repositorio bloquea la fila del pedido (`select_for_update`): dos entregas del mismo pedido se serializan. `:201-206` — `OrderDeliverView` (`POST /api/orders/<id>/deliver/`, body `delivered_date`) y `RuleConflict` 409 `{code, detail}` (`:57-61`).
- `backend/modules/sales/api/serializers.py:46-48` — `order_code` («P-XXXXXXXX») es la etiqueta visible del pedido; el identificador real es el UUID.
- `backend/modules/sales/infrastructure/adapters.py:1-35,37-46` — patrón de adaptadores sobre `services.py` de otros módulos y de integración opcional por `module_gate.is_enabled` (Clientes).
- `backend/modules/inventory/services.py:41-76` — fachada pública: `record_movement` (idempotente por `(source_type, source_id, source_line)`, producto, almacén y tipo; la política de negativo ya la lee `ModularityInventoryPolicy`), `reverse_movement`, `get_balance`. `allow_negative` **ya no** es parámetro público (PB-INV-007 merged).
- `backend/modules/inventory/application/movement_use_cases.py:34-73` — `RecordMovement` valida producto con `tracks_stock`, fracciones, almacén activo bajo `repository.locked(warehouse_id)` (`select_for_update` del almacén), reintento devuelve el existente, `_check_balance` lanza `InsufficientStock` (producto, almacén, solicitado, disponible) leyendo la política **dentro** del bloqueo.
- `backend/modules/inventory/domain/movement.py:34-41` — `sales_order` ya es una clase de origen (módulo propietario `sales`, etiqueta «Pedido de venta»).
- `backend/modules/inventory/infrastructure/django/movement_repository.py:96-101,110-116,173-175` — `locked`, `find_by_source` y `find_by_source_id(source_type, source_id)` (ya existe, sin exponer).
- `backend/modules/inventory/api/movement_views.py:69-77` y `movement_filters.py:37-62` — el origen se presenta con `available` (módulo propietario habilitado); la lista filtra por `source_type` pero **no por `source_id`**.
- `backend/modules/inventory/api/insufficient_stock.py:18-33` — 409 `insufficient_stock` con `product`, `warehouse`, `unit`, `requested`, `available` (una sola línea).
- `backend/modules/inventory/domain/warehouse.py` / `docs/adr/ADR-inventario-stock-almacenes-unidades-propiedad-y-fronteras.md:20` — siempre hay un almacén predeterminado (`is_default`), activo; PB-CFG-003 (almacén predeterminado configurable) **no existe** todavía.
- `backend/modules/sales/tests/test_boundaries.py:12-23` — mapa de dependencias: `'sales': {'catalog','customers','modularity'}`, `'inventory': {'catalog','modularity'}`; Sales aún no puede importar `inventory` (se amplía en esta tarea).
- `frontend/panel_admin/src/app/features/sales/pages/order-detail/order-detail.component.ts:132-152,185-202` — `runPrimary` → `deliver()` → `askDeliveryDate` (SweetAlert con fecha) → `api.deliver(id, date)`; `run()` ya bloquea doble envío con `busy`; `onError` recarga el pedido ante un 409.
- `frontend/panel_admin/src/app/features/sales/services/orders-api.service.ts:228-231` — `deliver(orderId, deliveredDate?)`.
- `frontend/panel_admin/src/app/features/inventory/models/movement.ts:4,11-23` — tipo `out` se etiqueta «Salida»; `SOURCE_ROUTES.sales_order` ya enlaza al pedido. `pages/movement-list/movement-list.component.ts:67-73` — la lista acepta `product_id`/`warehouse_id` por query string; falta `source_type`/`source_id`.
- `docs/design/design-system.md:134-136` — diálogos con `NgbModal` (patrón `warehouse-dialog`), bloqueos del servidor 409 en `alert alert-warning` con el motivo.
- `docs/tasks/TASK-politica-stock-negativo.md:30-32` — el usuario dejó explícito que la historia que descuente stock al entregar «consumirá la política ya lista»: esta es esa historia.

### Hipótesis / supuestos no confirmados
- «Referencia del pedido» = `order_code` (P-XXXXXXXX); «referencia de salida» = el mismo código, guardado en `reference` de cada movimiento (no se crea un número de salida nuevo).
- Con varios almacenes activos y sin PB-CFG-003 se preselecciona el almacén `is_default` (concepto ya existente) y se puede cambiar; con uno solo, ese. Cuando llegue PB-CFG-003 solo cambia de dónde sale el predeterminado.
- La lista de ítems controlados se decide **al entregar** con el `tracks_stock` vigente del producto (Catálogo ya bloquea cambiarlo si hay historial de movimientos).
- Los permisos son los vigentes: administrador de la empresa en una API con módulo habilitado. «Con los permisos correspondientes» se cumple con `available` (Ventas habilitado) que ya entrega el origen del movimiento.

### Módulos y dependencias relacionadas
`sales` (orquesta la entrega; nueva dependencia permitida sales → inventory, solo desde su adaptador), `inventory` (nuevas operaciones de fachada: salida en lote, lectura de saldos/almacenes/política, movimientos por origen; filtro `source_id`), `catalog` (indirecto), `modularity` (política, ya implementada). Frontend: `features/sales` (diálogo, detalle) y `features/inventory` (etiqueta, filtro por pedido).

### Implementaciones similares existentes
Adaptador opcional de Clientes (`sales/infrastructure/adapters.py:37-59`); ajuste de existencias (`inventory/application/adjustment_use_cases.py`) que ya registra movimientos con origen dentro de `locked()`; `warehouse-dialog` como diálogo `NgbModal`; `insufficient-stock-alert` para el aviso de saldo.

### Comportamiento actual
Entregar un pedido solo cambia su estado y fecha: no hay almacén, movimiento ni validación de saldo; Existencias no refleja las ventas.

### Restricciones
`CLAUDE.md`: aislamiento por `company_id` (la empresa sale del usuario, el `warehouse_id` se valida contra ella), cantidades `Decimal`, dominio sin Django, módulos de negocio sin importar `accounts` ni infraestructura ajena, no editar migraciones aplicadas, sin dependencias nuevas, frontend sin `any` y con Reactive Forms.

### Riesgos identificados
- Atomicidad y orden de bloqueos pedido → almacén (un solo almacén por entrega evita interbloqueos entre productos).
- Una entrega rechazada no debe dejar el pedido en `DELIVERED` (la excepción debe propagar y revertir `_run`).
- Los saldos del diálogo son informativos y pueden quedar viejos: el 409 debe poder re-mostrarse con valores actuales sin perder la fecha/almacén elegidos.
- La suite frontend tiene fallos preexistentes (comparar contra línea base). Concurrencia real solo verificable con PostgreSQL.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — primera integración transaccional Ventas → Inventario (nueva dependencia entre módulos, contrato API nuevo, atomicidad entre agregados).

### Diseño requerido
**SI** — diálogo de varios elementos con estados (almacén, saldo, política, errores), sección nueva en el detalle del pedido y cambios en Movimientos.

## Diseño
Ver `docs/design/DDR-ventas-inventario-salida-al-entregar-dialogo-entrega-y-detalle.md`.

## Arquitectura
Ver `docs/adr/ADR-ventas-inventario-salida-al-entregar-orquestacion-y-contrato.md`.

## Plan
Ver `docs/plans/PLAN-2026-10-29-ventas-inventario-salida-al-entregar.md` (v1 · COMPLETO · Specification READY).

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
