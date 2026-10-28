# TASK-inventario-movimientos-trazables: Registrar movimientos trazables de inventario (PB-INV-004)

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-inventario-movimientos-trazables
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/21

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-28 | (nuevo) → INVESTIGATION | Task creado desde `origin/main` (incluye PR #20) | delivery-start |
| 2026-10-28 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | NEEDS_ARCHITECTURE: nueva persistencia append-only, idempotencia/concurrencia, primera dependencia `inventory → catalog`, conexión de los puertos dejados por PB-INV-001/002 | delivery-start |
| 2026-10-28 | PLANNING → ENGINEERING | Specification READY (supuestos documentados en el Plan, ninguno bloqueante) | delivery-start |

## Investigación

### Requerimiento
**PB-INV-004 · Registrar movimientos trazables de inventario** (Inventario, P1, dep. PB-INV-001 y PB-INV-002). El administrador necesita un registro de entradas y salidas para conocer el origen de cada cambio de stock.

- Menú: Inventario → Movimientos; listado de solo lectura y detalle. Columnas: fecha/hora, referencia, producto, almacén, tipo, entrada, salida (columnas separadas), unidad y origen.
- Detalle: identificador, estado confirmado/revertido, empresa, producto, almacén, cantidad, tipo, fecha, usuario, referencia/motivo, origen y vínculos a contramovimientos. El vínculo al origen respeta permisos y módulo activo.
- Filtros: rango de fechas, producto, almacén, tipo y origen. Acciones: Ver detalle y abrir documento de origen; sin Editar ni Eliminar.
- AC: (1) cada movimiento guarda empresa, producto, almacén, tipo, cantidad positiva, fecha, usuario y documento de origen si existe; (2) saldo = entradas − salidas confirmadas, no se edita ni se borran movimientos confirmados; (3) una misma operación de origen no genera dos movimientos equivalentes, incluso con reintentos; (UI) repetir la confirmación de un documento fuente deja una sola entrada/salida visible y el detalle permite reconstruir la operación.

### Hechos encontrados
- `backend/modules/inventory/` existe (PB-INV-002): solo `Warehouse` (`domain/warehouse.py`, `infrastructure/django/models.py:1-30`, migración `0001_stock_units_warehouses.py`), `api/` con `required_modules = ('inventory',)` (`api/views.py`), `application/use_cases.py`, `application/ports.py:5-11` (`WarehouseActivity`) y su adaptador nulo `infrastructure/activity.py:4-16` (siempre «no»). No hay movimientos ni saldos.
- `backend/shared/stock_history.py:1-31` — puerto `register(provider)` / `has_history(company_id, product_id)`; sin proveedor responde `False`. El ADR de PB-INV-001/002 (`docs/adr/ADR-inventario-stock-almacenes-unidades-propiedad-y-fronteras.md`, Estrategia de rollback) dice que la historia de movimientos **debe** registrar ese proveedor y sustituir el adaptador nulo.
- `backend/modules/catalog/infrastructure/django/models.py:6-45` — `UnitModel` (nombre, abreviatura, `allows_fractions`) y `ProductModel` con `tracks_stock` y `base_unit` FK `PROTECT`. `backend/modules/catalog/services.py:1-33` — fachada pública solo con `get_product_for_sale`; no expone datos de inventario del producto.
- `backend/modules/sales/tests/test_boundaries.py:11-20` — `ALLOWED_DEPENDENCIES['inventory'] = set()`; las dependencias entre módulos solo por `services.py` y desde adaptadores de infraestructura (`CONSUMERS`, línea 23). `modularity/domain/modules.py:24-25` ya declara `inventory` requiere `catalog`, opcional `sales`/`purchases`.
- `backend/modules/sales/infrastructure/adapters.py:1-60` — patrón de adaptador que consume fachadas de otros módulos y `shared.module_gate`.
- `backend/modules/modularity/apps.py:8-13` — `ready()` registra el proveedor del gate; mismo lugar/patrón para registrar el proveedor de historial.
- `backend/modules/expenses/api/filters.py:1-50` — parseo de filtros con 400 por parámetro (fecha `AAAA-MM-DD`, UUID) a reutilizar como patrón; `inventory/api/pagination.py` ya existe.
- `frontend/panel_admin/src/app/app.routes.ts:90-121` — rutas `inventory`, `inventory/configuration`, `inventory/settings` con `moduleGuard`; `assets/data/routes.json:170-201` — submenú Inventario (Inicio, Configuración, Ajustes). `features/inventory/` (PB-INV-002) con servicios de unidades/almacenes reutilizables para los selectores de filtro. `features/expenses/expenses.routes.ts` — patrón de rutas lista/detalle.
- `docs/architecture/ddd.md` — nota de inventario base y sección 26 (`StockMovement` como evolución futura); `docs/design/design-system.md` §5 plantillas Lista y Detalle.
- No existe aún ningún documento de origen que genere movimientos: Ventas/Compras no tocan inventario (fuera del alcance de PB-INV-001/002).

### Hipótesis / supuestos no confirmados
- Los movimientos los crean los casos de uso de otras historias (ventas, compras, ajustes) a través de una **fachada** de Inventario; este task no ofrece un endpoint HTTP para crearlos (la UI es de solo lectura).
- «Tipo» = dirección (Entrada/Salida); «origen» = clase de documento fuente (Pedido de venta, Recepción de compra, Ajuste de inventario) o «Sin documento».
- Solo el administrador de la empresa accede (único rol hoy).

### Módulos y dependencias relacionadas
`inventory` (propietario), `catalog` (nombre/unidad del producto vía `catalog.services`, nueva dependencia declarada `inventory → catalog`), `shared.module_gate` (módulo de origen habilitado), `shared.stock_history`, frontend `features/inventory`, `layout/sidebar`.

### Implementaciones similares existentes
`inventory` Warehouse (CRUD por empresa), `expenses` (lista con filtros por fecha/categoría, paginada, detalle), `modularity_setting_change` (registro append-only).

### Comportamiento actual
Inventario no registra cambios de stock; los puertos de historial y actividad de almacén responden «no».

### Restricciones
`company_id` en toda consulta; cantidades en `Decimal` (nunca `float`); migración nueva (no editar la existente); sin dependencias nuevas (`pip`/`npm`); dominio sin Django; módulos solo se llaman por `services.py`; no hay eliminar/editar de movimientos.

### Riesgos identificados
Reintentos y concurrencia (doble movimiento por la misma operación); saldo negativo por salidas simultáneas; consumo de un nuevo módulo (`catalog`) por `inventory`; `stock_history` activa bloqueos reales en productos al aparecer el primer movimiento; el vínculo al origen apunta a pantallas que dependen de otros módulos.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — nuevo agregado append-only con garantías de idempotencia y de saldo bajo concurrencia, nueva dependencia entre módulos, y activa en producción los puertos de historial y actividad de almacén.

### Diseño requerido
**SI** — dos pantallas nuevas (lista con filtros y detalle de solo lectura) y un ítem de menú.

## Diseño
Ver `docs/design/DDR-inventario-movimientos-trazables-lista-y-detalle-movimientos.md`.

## Arquitectura
Ver `docs/adr/ADR-inventario-movimientos-trazables-registro-idempotente-y-saldo.md`.

## Plan
`docs/plans/PLAN-2026-10-28-inventario-movimientos-trazables.md` (v1, COMPLETO, READY).

## Implementación

**Backend** (`backend/modules/inventory/`): dominio `movement.py` (StockMovement, MovementSource, catálogo `SOURCE_TYPES`; INV-01, 02, 07), casos de uso `movement_use_cases.py` (RecordMovement idempotente + control de saldo bajo bloqueo del almacén, ReverseMovement; INV-03..06), repositorio `movement_repository.py`, adaptador de catálogo `infrastructure/adapters.py`, fachada `services.py` (`record_movement`, `reverse_movement`, `get_balance`, `has_history`), migración `0002_stock_movements` (restricciones únicas parciales, check `quantity > 0`, índices), API de solo lectura `GET /api/stock-movements/[<id>/]` con filtros y `source.available` (AC-04..07), conexión de puertos (`apps.py` registra `stock_history`; `LedgerWarehouseActivity` reemplaza el adaptador nulo; INV-09, AC-09). `catalog.services.get_products_for_inventory` (nueva fachada). Test de fronteras: `inventory: {'catalog'}` y `inventory` en `CONSUMERS`.

**Frontend** (`features/inventory`): `MovementsApiService`, modelos, `MovementListComponent` (filtros, columnas Entrada/Salida separadas) y `MovementDetailComponent`, `inventory.routes.ts`, ruta `inventory/movements`, ítem de menú (`routes.json`, i18n es/en/de). Pantallas de referencia: `expense-list` y `expense-detail`; patrón nuevo documentado en `design-system.md` («Lista de solo lectura con filtros»). Componentes reutilizados: `ngx-datatable`, badges, `AuthService` (nombre de empresa de la sesión).

**Pruebas escritas:** `inventory/tests/test_movements.py` (dominio, fachada, idempotencia secuencial y concurrente, saldo, reversión, puertos, API, aislamiento), `catalog/tests/test_services.py`, specs Karma (servicio, lista, detalle, menú).

**Desviaciones respecto al plan v1:**
- Filtro de producto con `form-select` (primeros 100 productos) en lugar de `ng-select` del DDR; evita una dependencia de UI para esta pantalla. Deuda: productos > 100.
- El contramovimiento no repite el `source` (se vincula por `reverses_id`) para no chocar con la idempotencia; el plan no lo especificaba.
- Se añadieron `application/movement_ports.py`, `api/movement_filters.py`, `api/movement_urls.py` (archivos no listados en el plan).

**Verificación propia (no es el Quality Gate):** `manage.py check` OK; migración generada con `makemigrations`; tests sin BD (dominio + fronteras, 12) OK. Frontend: `tsc` sin errores nuevos, Karma acotado (inventory + sidebar) 43/43 OK (con `app.component.spec.ts` apartado temporalmente, roto en `main`; restaurado), `ng lint` OK. **Pendiente:** los tests de backend con PostgreSQL (fachada, concurrencia, API, puertos, catálogo) **no se pudieron ejecutar**: este worktree no tiene `backend/.env` ni `DATABASE_URL`, y no se leen credenciales. Hay que correr `python manage.py test` con una BD de pruebas antes del Quality Gate.

## Review
_Pendiente_

## Publicación
_Pendiente_
