# TASK-inventario-consultar-existencias-historial: Consultar existencias e historial de movimientos (PB-INV-005)

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** SI
**Rama:** task/TASK-inventario-consultar-existencias-historial
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/24

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-28 | (nuevo) → INVESTIGATION | Task creado desde `origin/main` (incluye PR #21 PB-INV-004 y #22 PB-INV-003) | delivery-start |
| 2026-10-28 | INVESTIGATION → DESIGN → PLANNING | NEEDS_PLAN: extiende lectura existente (sin migraciones, sin persistencia nueva); decisión del usuario sobre ajuste/apertura | delivery-start |
| 2026-10-28 | PLANNING → ENGINEERING | Specification READY | delivery-start |
| 2026-10-28 | ENGINEERING → REVIEW | Implementación completa según plan v1; backend 796 OK, build, lint y Karma acotado OK | delivery-build |
| 2026-10-28 | REVIEW → PUBLISH | Quality Gate PASS (primer ciclo); REV-01 y REV-02 Low abiertos; a la espera de aprobación humana | delivery-publish |

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
**Backend.** `catalog.services.list_products_for_inventory` (+`active` en `ProductForInventory`; INV-02, INV-03). `inventory`: `domain/stock.py` (`BalanceState`, `balance_state`; INV-04), `StockPositionNotFound`, puerto `ProductDirectory.list_stock_products` y su adaptador, `application/stock_use_cases.py` (`ListStock` recompone productos × almacenes con los saldos del libro y filtra; `GetStockPosition`, `can_register_opening`; INV-01, INV-05), `api/stock_views.py` (`GET /api/stock/` con `search`, `warehouse_id`, `active`, `balance`, 400 por parámetro; `GET /api/stock/<product_id>/<warehouse_id>/`; API-01, API-02), serializers y URL. Sin migraciones.
**Frontend** (`features/inventory`). `stock.ts`/`stock-api.service.ts` (filtros, `get`, `balanceState`), `stock-list` (buscador, almacén, estado del producto, saldo, «Limpiar», columna Unidad base, «Negativo» con texto, badge «Inactivo», enlace al detalle; UI-01, UI-03), `stock-detail` nueva (datos, «Ver movimientos», «Registrar apertura» condicionada con nota, historial de 10 por página con enlace al movimiento y al documento de origen; UI-02), ruta `inventory/stock/:productId/:warehouseId`, y `movement-list` incluye siempre el producto prefiltrado en el selector (REV-09; AC-06). Docs: `design-system.md` (patrón «Detalle con historial embebido» y menú), `ddd.md`, `modulos-implementados.md`.
**Pruebas.** Backend: `inventory/tests/test_stock_query.py` (AC-01, 02, 04, 05, 07, 08, EDGE-01..06, INV-04, INV-05), `catalog/tests/test_services.py` (listado), `test_stock.py` adaptado al nuevo contrato. Frontend: specs de `stock-api.service`, `stock-list`, `stock-detail` (nueva) y `movement-list`.
**Pantallas de referencia:** `product-detail` (Detalle) y `stock-list`/`movement-list` (Lista); componentes reutilizados: `badge-outline`, `NgbPagination`, `_inventory-table.scss`; no se creó nada en `shared/`.
**Desviaciones respecto al plan:** (0) se reutilizaron `list_balances()` y `products_with_history()` del repositorio en lugar de crear `balances_by_pair()` y `has_history_in()` (mismo resultado, menos API; `list_balances()` agrega el libro completo, riesgo ya anotado); (1) el filtro «Estado del producto» y «Saldo» se aplican en memoria sobre la composición, como indicaba el riesgo del plan; (2) «Registrar apertura» del detalle enlaza con `?warehouse_id=` (el formulario ya lo lee). Ninguna otra.
**Deuda técnica:** composición en memoria productos × almacenes (migrar a consulta en BD si crece el volumen); el filtro de producto de movimientos sigue siendo un `form-select` de 100 productos más el prefiltrado; revisión visual en navegador pendiente.
**Verificación propia (no es el Quality Gate):** backend `manage.py test` 796 OK; `makemigrations --check` sin cambios; frontend `npm run lint` OK, `ng build` OK, Karma acotado a `features/inventory` 85/85 OK (con `app.component.spec.ts` apartado temporalmente por estar roto en `main`; restaurado). Entorno: con autorización del usuario se copió `backend/.env` del checkout principal (sin abrirlo; ignorado por git), se usó su `.venv` y se enlazó `node_modules`.

## Review
**Ciclo 1: PASS** (subagente aislado). Backend 796 tests OK, `makemigrations --check` sin cambios, bandit (inventory, catalog) 0 hallazgos, `test_boundaries` OK. Frontend: lint OK, `ng build` OK, Karma `features/inventory` 85/85 OK; Karma `layout` 19 OK y 1 fallo (`FooterComponent should create`, icono Feather) = línea base rota, fuera del diff. `npm audit` no ejecutable (sin lockfile). Revisión visual en navegador (móvil/escritorio/oscuro): **no verificada** (checklist §8 revisada por código).
**Corregidos tras el Gate (REV-01 con test de 403 del detalle, REV-02 documentando la desviación en `## Implementación`).** Hallazgos originales: [REV-01](../reviews/REV-2026-10-28-inventario-consultar-existencias-historial-01.md) falta test de 403 (módulo deshabilitado / no administrador) del nuevo detalle; [REV-02](../reviews/REV-2026-10-28-inventario-consultar-existencias-historial-02.md) desviación no documentada: se reutilizaron `list_balances()` y `products_with_history()` en lugar de crear `balances_by_pair()`/`has_history_in()` (el plan los listaba); `list_balances()` agrega todo el libro, riesgo ya anotado.

## Publicación
PR 24 listo para aprobación humana; no se mergea desde el flujo. Sin cambios sensibles: no hay ADR, migraciones, ni cambios de autenticación o infraestructura; los endpoints nuevos conservan `CompanyAdminPermission` y módulo `inventory`. Cambio de contrato a validar: las filas de `GET /api/stock/` ahora incluyen todos los productos con control de stock (también sin movimientos).
