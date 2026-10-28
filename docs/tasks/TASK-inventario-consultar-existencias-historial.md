# TASK-inventario-consultar-existencias-historial: Consultar existencias e historial de movimientos (PB-INV-005)

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** SI
**Rama:** task/TASK-inventario-consultar-existencias-historial
**Pull Request:** _sin abrir todavía_

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-28 | (nuevo) → INVESTIGATION | Task creado desde `origin/main` (incluye PR #21 PB-INV-004 y #22 PB-INV-003) | delivery-start |
| 2026-10-28 | INVESTIGATION → DESIGN → PLANNING | NEEDS_PLAN: extiende lectura existente (sin migraciones, sin persistencia nueva); decisión del usuario sobre ajuste/apertura | delivery-start |
| 2026-10-28 | PLANNING → ENGINEERING | Specification READY | delivery-start |

## Investigación

### Requerimiento
**PB-INV-005 · Consultar existencias e historial de movimientos** (Inventario, P1, dep. PB-INV-004). Como usuario, quiero consultar stock e historial para saber qué tengo disponible y por qué cambió.

- Menú Inventario → Existencias: listado por producto/almacén y detalle del producto en ese almacén.
- Columnas: producto, almacén, unidad base y cantidad actual. Sin «disponible», «reservado» ni valoración.
- Filtros: búsqueda por nombre de producto, almacén, activo/inactivo y saldo cero / no cero / negativo (el negativo se distingue con texto además del color).
- Detalle: nombre, unidad, almacén, saldo actual e historial filtrado al producto/almacén. Acciones: Ver movimientos, Registrar apertura si cumple condiciones, Registrar ajuste.
- Interfaz: el saldo coincide con el historial confirmado; un producto sin movimientos tiene saldo cero (no error); el detalle conserva productos inactivos cuando se incluyen por filtro.
- AC: (1) saldo actual por producto y almacén en unidad base; (2) el historial filtra por producto, almacén, fecha y tipo y permite identificar el documento de origen; (3) productos inactivos mantienen su historial y todo se limita a la empresa de la sesión.

**Aclaración del usuario (2026-10-28):** «Registrar ajuste» queda **fuera de alcance** (no existe alta manual de movimientos; se entrega con su propia historia). «Registrar apertura» sí existe (PB-INV-003) y se ofrece en el detalle cuando cumple condiciones.

### Hechos encontrados
- `backend/modules/inventory/api/stock_views.py:StockListView` — `GET /api/stock/` hoy devuelve solo pares producto/almacén **con movimientos**, ordenados por almacén y UUID de producto, filtro único `warehouse_id`; sin búsqueda por nombre, estado activo ni estado de saldo; el nombre se resuelve después de paginar.
- `backend/modules/inventory/infrastructure/django/movement_repository.py:181-187` — `list_balances(warehouse_id)` agrega `Σ entradas − Σ salidas` del libro (mismo cálculo que `get_balance`, `:89-92`), así que lista y fachada coinciden.
- `backend/modules/catalog/services.py:42-52` — `get_products_for_inventory(company_id, ids)` sin listado; `ProductForInventory` no trae `active`. No hay forma de listar productos que controlan stock con filtros desde Inventario sin otra consulta a catálogo.
- `backend/modules/inventory/infrastructure/adapters.py` — único punto de Inventario que conoce a Catalog, por su `services.py`; `application/movement_ports.py` define `ProductDirectory`.
- `backend/modules/inventory/api/movement_filters.py` y `movement_views.py` — la lista de movimientos (PB-INV-004) ya filtra por fecha, producto, almacén, tipo y origen y entrega `source` con `available`; el detalle de movimiento ya muestra el origen. Aplican AC-2 sin cambios de backend.
- `frontend/panel_admin/src/app/features/inventory/pages/stock-list/stock-list.component.ts` — lista mínima: solo filtro de almacén (activos), sin buscador/estado/saldo, sin saldo negativo diferenciado, sin detalle; `openMovements()` navega a movimientos con `?warehouse_id=&product_id=`.
- `frontend/panel_admin/src/app/app.routes.ts:109-126` — rutas `inventory/stock` y `inventory/stock/opening`; no hay detalle. `assets/data/routes.json` ya tiene «Existencias».
- `docs/tasks/TASK-registrar-existencias-iniciales.md` (REV-08/REV-09 abiertos) — limitación: Existencias ordena por UUID, no por nombre; el filtro de producto de movimientos solo carga 100 productos (REV-09).
- `backend/modules/inventory/api/stock_views.py:OpeningCheckView`, `application/stock_use_cases.py:RegisterOpening` — la apertura solo se admite para producto+almacén **sin movimientos**; esa es la «condición» de «Registrar apertura».
- `docs/design/design-system.md` §5 (Lista, Detalle, Lista de solo lectura con filtros); `docs/design/DDR-registrar-existencias-iniciales-pantallas-existencias-apertura.md` define la pantalla actual de Existencias.

### Hipótesis / supuestos no confirmados
- Las filas de Existencias son **todos los productos que controlan stock × los almacenes**, de modo que un producto sin movimientos aparece con saldo 0 y el filtro «saldo cero» tiene sentido. Por defecto: productos activos y almacenes activos; un almacén inactivo aparece solo si se elige en el filtro (su saldo es 0 porque no se puede desactivar con saldo ≠ 0).
- Filtro de estado del producto: `Activos` (por defecto) / `Inactivos` / `Todos`.
- Saldo negativo solo es posible con `allow_negative` (otras historias); se muestra con texto «Negativo» además del color.
- «Historial confirmado»: el saldo es Σ de todo el libro; una reversión suma el contramovimiento y el original queda «revertido», así que el neto coincide con los movimientos confirmados.
- El volumen de MVP permite componer en memoria (productos de catálogo × almacenes × saldos agregados) y paginar; se anota como riesgo.

### Módulos y dependencias relacionadas
`inventory` (dueño de saldos y movimientos), `catalog` (listado de productos solo por `catalog.services`), `modularity` (gate `inventory`), frontend `features/inventory`.

### Implementaciones similares existentes
`StockListView`/`ListStock` (PB-INV-003), `MovementListComponent` (filtros), `product-list`/`product-detail` (plantillas Lista/Detalle).

### Comportamiento actual
Existencias lista solo pares con movimientos y no permite buscar ni filtrar por estado o saldo; no hay detalle; el historial de un par se consulta saltando a la lista de movimientos.

### Restricciones
`company_id` en todo; `Decimal` (el saldo viaja como texto); sin migraciones ni dependencias nuevas; dominio sin Django; entre módulos solo `services.py`.

### Riesgos identificados
Composición en memoria con muchos productos × almacenes; filtro de producto de movimientos limitado a 100 (REV-09); cambio de contrato de `GET /api/stock/` (el consumidor es solo la pantalla Existencias y el formulario de apertura no lo usa).

### Veredicto de complejidad
**NEEDS_PLAN** — extiende lectura existente sin migraciones, sin permisos nuevos ni integración nueva (la dependencia `inventory → catalog` ya existe); comportamiento de dominio de lectura (saldos) nuevo, por lo que el plan es COMPLETO.

### Diseño requerido
**SI** — filtros nuevos y una pantalla de detalle.

## Diseño
`docs/design/DDR-inventario-consultar-existencias-historial-existencias-y-detalle.md`

## Arquitectura
No aplica según veredicto.

## Plan
`docs/plans/PLAN-2026-10-28-inventario-consultar-existencias-historial.md` (v1, COMPLETO, READY).

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
