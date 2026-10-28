# TASK-registrar-existencias-iniciales: Registrar existencias iniciales (PB-INV-003)

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-registrar-existencias-iniciales
**Pull Request:** _sin abrir todavía_

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-27 | (nuevo) → INVESTIGATION | Task creado; rama integrada con `origin/main` (PR #20 con PB-INV-001/002 ya publicado) | delivery-start |
| 2026-10-27 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | NEEDS_ARCHITECTURE: primeras tablas de movimientos y saldos, conexión de los puertos de historial y actividad de almacén, dependencia `inventory → catalog` | delivery-start |
| 2026-10-27 | PLANNING → ENGINEERING | Specification READY (sin decisiones de negocio abiertas; supuestos documentados en el Plan) | delivery-start |

## Investigación

### Requerimiento
**PB-INV-003 · Registrar existencias iniciales** (Inventario, P1, dep. PB-INV-001 y PB-INV-002). Como administrador, quiero cargar el stock inicial para comenzar a controlar mis productos.

- Acceso: Inventario → Existencias → «Registrar apertura» (formulario; sin menú independiente).
- Campos: almacén activo, fecha, referencia de apertura y líneas (producto que controla stock, unidad base de solo lectura, cantidad inicial no negativa).
- Acciones: agregar/quitar línea, revisar resumen, confirmar. El resumen muestra almacén, productos y cantidades; cancelar no produce movimientos.
- Interfaz: señalar la línea cuyo producto/almacén ya tiene movimientos; no permitir duplicados en el formulario; confirmar conduce a Existencias y permite abrir los movimientos; doble clic o reintento no duplica entradas.
- AC: (1) se registra producto, almacén, cantidad ≥ 0, fecha y referencia; (2) confirmar crea un movimiento de apertura y el saldo, y repetir la confirmación no duplica; (3) solo hay apertura sin movimientos anteriores para producto+almacén; las correcciones posteriores son ajustes.

### Hechos encontrados
- `backend/modules/inventory/` (PB-INV-002) solo tiene `Warehouse`: `domain/warehouse.py:68-102`, `application/use_cases.py`, `infrastructure/django/models.py:7-25`, `api/views.py:46-113`, migración `0001_stock_units_warehouses.py`. No existen movimientos ni saldos.
- `backend/modules/inventory/application/ports.py:6-11` y `infrastructure/activity.py:5-14` — `WarehouseActivity` con adaptador nulo (`NoWarehouseActivity`), usado en `api/views.py:96-99` (`DeactivateWarehouse`). Hoy nunca bloquea; este task tiene datos reales para sustituirlo (saldo ≠ 0).
- `backend/shared/stock_history.py:7-24` — puerto `register(provider)` / `has_history(company_id, product_id)`; sin proveedor registrado responde `False`. Catálogo lo consulta al cambiar unidad o control de stock (ADR previo, `docs/adr/ADR-inventario-stock-almacenes-unidades-propiedad-y-fronteras.md`, decisión 3). Nadie lo registra aún.
- `backend/modules/catalog/services.py:1-33` — fachada `get_product_for_sale` con DTO; no expone `tracks_stock` ni la unidad base.
- `backend/modules/catalog/domain/unit.py:30-60` — `UnitOfMeasure` con `allows_fractions`; `catalog/api/serializers.py:19-23` — `BaseUnitSerializer` solo entrega id, nombre y abreviatura (falta `allows_fractions`, necesario para validar cantidades fraccionarias en la UI).
- `backend/modules/catalog/api/views.py:61-67` y `infrastructure/django/repositories.py:54-60` — la lista de productos filtra solo por `search` y `active`; no hay filtro `tracks_stock`.
- `backend/modules/sales/tests/test_boundaries.py:11-20` — `ALLOWED_DEPENDENCIES['inventory'] = set()`; la apertura exige `inventory → catalog` (declarado en `modularity/domain/modules.py:23-25`, `requires=('catalog',)`).
- `backend/modules/sales/infrastructure/django/models.py:22-62` — convención de importes `Decimal` y `CheckConstraint`; `company_id` UUID sin FK entre módulos (`inventory/infrastructure/django/models.py:10`).
- `backend/config/urls.py:14` — solo `api/warehouses/`; `api/stock/` no existe. `inventory/apps.py` sin `ready()`.
- `frontend/panel_admin/src/app/app.routes.ts:60-110` — rutas `inventory` (placeholder), `inventory/configuration`, `inventory/settings`, todas con `moduleGuard`; `assets/data/routes.json:170-201` — submenú Inventario: «Inicio», «Almacenes y unidades», «Ajustes». No hay «Existencias».
- `frontend/panel_admin/src/app/features/inventory/` — `UnitsApiService`, `WarehousesApiService`, modelos, `_inventory-table.scss`; `features/products/models/product.ts:1-32` ya expone `tracksStock` y `baseUnit`.
- `docs/design/design-system.md:95-137` — plantillas Lista, Formulario, Detalle, Configuración con pestañas y sección condicionada por módulo.

### Hipótesis / supuestos no confirmados
- «Existencias» no existe como pantalla: se crea una pantalla mínima de saldos por almacén y de movimientos de un producto+almacén, solo lo necesario para cumplir «conduce a Existencias y permite abrir sus movimientos». Búsqueda avanzada, kardex completo y ajustes son otras historias.
- Cantidad cero se admite (el criterio dice «no negativa») y cuenta como movimiento: impide una segunda apertura y se corrige con ajuste.
- La fecha de apertura no puede ser futura (la historia no lo dice; el stock inicial es un hecho pasado o de hoy).
- La referencia es obligatoria (se registra «referencia de apertura»), máx. 100 caracteres; no se exige única.
- Solo el administrador (`CompanyAdminPermission` por defecto) registra aperturas.
- Un producto inactivo que controla stock no se ofrece en el formulario, pero el backend solo exige que controle stock.

### Módulos y dependencias relacionadas
`inventory` (dueño de movimientos, saldos, aperturas), `catalog` (producto y unidad base, solo por `catalog.services`), `shared.stock_history`, `modularity` (gate del módulo `inventory`), frontend `features/inventory`, `features/products`, `layout/sidebar`.

### Implementaciones similares existentes
Backend: casos de uso y repositorio de almacenes (`inventory/application/use_cases.py`), `sales` (agregado con líneas + fachada de catálogo + `transaction.atomic`). Frontend: `features/sales/pages/order-form` (formulario con líneas), `features/inventory` (servicios y modelos).

### Comportamiento actual
No se puede cargar stock: no hay tablas de movimientos/saldos, ni pantalla de existencias; los bloqueos por historial y saldo están implementados pero siempre responden «sin historial».

### Restricciones
`CLAUDE.md`: aislamiento por `company_id` desde el usuario, cantidades en `Decimal` (nunca `float`), migraciones nuevas y aditivas, dominio sin Django, módulos solo por `services`/puertos, sin dependencias nuevas, sin CQRS/event sourcing.

### Riesgos identificados
- Doble envío o carrera: dos confirmaciones simultáneas con la misma o distinta clave para el mismo producto+almacén.
- Al conectar `stock_history`, Catálogo empieza a bloquear cambios de unidad/control de stock tras la apertura (comportamiento esperado de PB-INV-001, ahora con datos reales).
- Cantidades fraccionarias en unidades que no las admiten.
- Suite frontend con 71 specs demo rotos preexistentes: comparar contra la línea base.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — primeras tablas de movimientos y saldos (modelo de datos que luego heredan ajustes, compras y ventas), idempotencia, conexión de puertos entre módulos, nueva dependencia `inventory → catalog`.

### Diseño requerido
**SI** — pantalla nueva de Existencias, formulario con líneas y paso de resumen/confirmación, estados de bloqueo por historial.

## Diseño
`docs/design/DDR-registrar-existencias-iniciales-pantallas-existencias-apertura.md`

## Arquitectura
`docs/adr/ADR-registrar-existencias-iniciales-movimientos-saldos-idempotencia.md`

## Plan
`docs/plans/PLAN-2026-10-27-registrar-existencias-iniciales.md` (v1, COMPLETO) · Specification readiness: READY

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
