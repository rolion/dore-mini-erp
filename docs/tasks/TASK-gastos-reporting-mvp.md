# TASK-gastos-reporting-mvp: Módulo Gastos (categorías, gastos, anulación, método de pago) y módulo Reporting (dashboard y reportes de ventas/gastos)

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** `task/TASK-gastos-reporting-mvp`
**Pull Request:** _sin abrir todavía_

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-09 | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-10-09 | DESIGN → ARCHITECTURE | Decisión de diseño registrada en 2 DDR (menú y pantallas de gastos/categorías; dashboard y reportes) | delivery-design |
| 2026-10-09 | ARCHITECTURE → PLANNING | Decisiones registradas en 5 ADR (modelo de dominio de gastos, contrato API de gastos, lectura entre módulos, contrato API de reportes, features frontend); reglas de negocio confirmadas por el usuario | delivery-architect |
| 2026-10-09 | PLANNING → ENGINEERING | Plan v1 COMPLETO, Specification READY; rama creada desde `origin/main` (Sales incluido); PR abierto | delivery-plan |

## Investigación

### Requerimiento
Objetivo: registrar las salidas de dinero del negocio y clasificarlas de forma simple para entender en qué se gasta. Alcance recibido: REQ-EXP-001 a REQ-EXP-007 (dominio Expenses) y REQ-REP-001 a REQ-REP-010 (dominio Reporting).

**Expenses**
- **REQ-EXP-001 Crear categoría de gasto** (MVP-Alta, sin dep.): nombre obligatorio; las categorías pueden desactivarse sin borrar historial. Aceptación: la categoría creada queda disponible al registrar gastos.
- **REQ-EXP-002 Registrar gasto** (MVP-Alta, dep. 001): mínimos descripción, monto, categoría y fecha; monto > 0; notas y proveedor opcionales. Aceptación: un gasto válido aparece en consultas del periodo; monto cero o negativo se rechaza.
- **REQ-EXP-003 Editar gasto** (MVP-Alta, dep. 002): mismas validaciones que la creación; la edición actualiza reportes posteriores.
- **REQ-EXP-004 Anular o eliminar gasto** (MVP-Media, dep. 002): preferir anulación lógica para conservar trazabilidad; un gasto anulado no suma en reportes normales.
- **REQ-EXP-005 Listar y filtrar gastos** (MVP-Alta, dep. 002): filtros mínimos rango de fechas y categoría.
- **REQ-EXP-006 Gestionar categorías** (MVP-Media, dep. 001): editar y desactivar; una categoría usada históricamente no se borra físicamente; una inactiva no se ofrece para nuevos gastos; los gastos históricos conservan su categoría.
- **REQ-EXP-007 Método de pago del gasto** (MVP-Media, dep. 002): efectivo, QR, transferencia, tarjeta, otro; visible en el detalle.

**Reporting** (consulta otros módulos, no modifica sus entidades)
- **REQ-REP-001 Resumen de dashboard** (MVP-Alta): ventas, gastos, ganancia estimada, cantidad de pedidos, pendientes de entrega y de cobro; periodo seleccionable (día, semana, mes); valores coherentes con Sales y Expenses.
- **REQ-REP-002 Ventas por periodo** (MVP-Alta, dep. REQ-SAL-014): criterio explícito (pedidos válidos y definición de ingreso); sin cancelados salvo vista comparativa; devuelve total y cantidad de pedidos.
- **REQ-REP-003 Gastos por periodo** (MVP-Alta, dep. REQ-EXP-005): suma de gastos válidos; los anulados no se incluyen.
- **REQ-REP-004 Gastos por categoría** (MVP-Alta, dep. REQ-EXP-005): la suma de categorías coincide con el total del mismo periodo.
- **REQ-REP-005 Ganancia estimada** (MVP-Alta, dep. 002 y 003): ingresos considerados − gastos registrados; etiqueta explícita "Ganancia estimada", sin insinuar costo real de producción; reproducible.
- **REQ-REP-006 Productos más vendidos** (MVP-Media, dep. REQ-SAL-002): por unidades e importe, respeta el rango, usa los snapshots de `OrderItem`.
- **REQ-REP-007 Ventas por canal** (MVP-Media, dep. REQ-SAL-007): agrupa por `SalesChannel` del pedido.
- **REQ-REP-008 Clientes con mayor compra** (MVP-Media, dep. REQ-CUS-004 y REQ-SAL-014): ranking por total comprado y número de pedidos, solo pedidos válidos.
- **REQ-REP-009 Ticket promedio** (MVP-Media, dep. 002): total de ventas / cantidad de pedidos considerados; sin división por cero; con 0 pedidos devuelve 0 o estado vacío sin error.
- **REQ-REP-010 Pendientes de entrega y cobro** (MVP-Alta, dep. REQ-SAL-013 y 016): listas accionables; pendiente de entrega se deriva del estado, pendiente de cobro del saldo y `PaymentStatus`; un pedido DELIVERED con PARTIAL aparece como pendiente de cobro, no de entrega.

### Hechos encontrados

**Estado del repositorio y de la rama**
- La rama de trabajo `claude/expense-management-system-c7d676` está en `b43956f` y **está por detrás de `main`** (`f7af20f`, merge del PR #7 `TASK-ciclo-pedido-entrega-cobro`). En esta rama **no existe `modules/sales`**; en `main` sí (`git ls-tree main backend/modules/sales`, 34 archivos incl. `domain/order.py`, `domain/enums.py`, `infrastructure/django/models.py`, `api/urls.py`, `tests/test_boundaries.py`). Los hechos sobre Sales de abajo se leyeron en `main`.
- En esta rama `backend/modules/` solo tiene `accounts`, `catalog`, `customers`; **no existen `expenses` ni `reporting`** (ni en `main`). `backend/config/urls.py:6-11` monta `admin`, `health`, `auth`, `products`, `customers` (en `main` se añade `api/orders/` → `modules.sales.api.urls`). `INSTALLED_APPS` registra `modules.accounts|catalog|customers` en `backend/config/settings/base.py:20-22` (en `main` además `modules.sales`).
- `backend/shared/` solo contiene `__init__.py`; no existe `Money`, `DateRange` ni excepciones compartidas (previstos en `docs/architecture/ddd.md` sección de estructura).

**Diseño documentado (`docs/architecture/ddd.md`)**
- `ddd.md:571-662` — Expenses: agregado `Expense` con `id, description, amount, category_id, expense_date, payment_method, supplier_name, notes, receipt_url, created_at, updated_at`; entidad `ExpenseCategory`; `ExpenseType` (VARIABLE/FIXED) "opcional"; reglas de dominio (monto > 0, fecha obligatoria, categoría obligatoria, categorías usadas no se borran físicamente, "puede modificarse mientras no haya sido bloqueado por un cierre contable futuro"); commands `CreateExpense, UpdateExpense, DeleteExpense, CreateExpenseCategory, UpdateExpenseCategory, DeactivateExpenseCategory`; queries `GetExpense, ListExpenses, ListExpensesByDateRange, ListExpensesByCategory, ListExpenseCategories`.
- `ddd.md:666-750` — Reporting: queries `GetDashboardSummary, GetSalesReport, GetExpenseReport, GetProfitabilityReport, GetSalesByProduct, GetSalesByChannel, GetTopCustomers, GetMonthlyTrend`; "Reporting puede leer … nunca modificar". `ddd.md:706` define "Resultado simple = **Ventas cobradas** − Gastos registrados" y `ddd.md:709` exige llamarlo "resultado simple" o "ganancia estimada".
- `ddd.md:432-440` — `PaymentMethod` (CASH, QR, BANK_TRANSFER, CARD, OTHER) está definido en el apartado de Sales; en `main` es `modules/sales/domain/enums.py` (`PaymentMethod`). Los valores coinciden con los de REQ-EXP-007.
- `ddd.md:960-977` (endpoints previstos): `GET/POST /api/expenses`, `PATCH /api/expenses/{id}`, `DELETE /api/expenses/{id}`, `GET/POST /api/expense-categories`, `GET /api/reports/dashboard`, `GET /api/reports/expenses`. `ddd.md:1067-1090`: Angular `features/expenses/` (`expense-list`, `expense-form`) y `features/dashboard/` (`expense-summary`).
- `ddd.md:809` (en `main`) — convención: la única vía entre módulos es la fachada `modules/<modulo>/services.py` con DTO inmutables; `test_boundaries.py` la verifica.
- `docs/adr/ADR-ciclo-pedido-entrega-cobro-integracion-modulos.md` (en `main`): "**Reporting** leerá las tablas/consultas de Sales por su propia capa de lectura (otro task)" — decisión explícitamente diferida a este trabajo.

**Sales en `main` (fuente de datos de Reporting)**
- `backend/modules/sales/infrastructure/django/models.py` (`main`): `OrderModel` (tabla `sales_order`) con `status`, `sales_channel`, `order_date`, `expected_delivery_date`, `delivered_date`, `customer_id` (UUID sin FK), importes **persistidos** `subtotal/discount/total/paid_total` (Decimal 12,2) y `payment_status` (indexados); `OrderItemModel` (`sales_order_item`) con snapshot `product_id/product_name/unit_price/quantity/subtotal`; `PaymentModel` (`sales_payment`) con `amount`, `payment_method`, `payment_date`.
- `modules/sales/domain/enums.py` (`main`): `OrderStatus` NEW/IN_PREPARATION/READY/DELIVERED/CANCELLED; `PaymentStatus` PENDING/PARTIAL/PAID/REFUNDED (REFUNDED "ningún flujo lo produce todavía"); `SalesChannel` WHATSAPP/FACEBOOK/INSTAGRAM/STORE/FAIR/OTHER.
- `modules/sales/domain/order.py:217-237` (`main`): `total = subtotal − discount`, `balance = total − paid_total`, `payment_status` derivado (PAID si `paid_total ≥ total`, PARTIAL si `> 0`, si no PENDING). `order.py:317-327`: `cancel()` solo cambia `status`, `cancellation_reason`, `cancelled_at`; **no toca los pagos ni `paid_total`**, por lo que un pedido CANCELLED puede conservar `paid_total > 0` y `payment_status` PAID/PARTIAL.
- `modules/sales/domain/repositories.py:20-47` (`main`): `OrderFilters` (estados, estados de pago, canal, cliente, `date_field`, rango `date_from/date_to`, `has_balance`, orden) y `OrderSummary` (modelo de lectura con `total`, `paid_total`, `balance`); `modules/sales/api/filters.py` los parsea desde query params de `GET /api/orders/` (`modules/sales/api/urls.py`, `main`). No hay endpoint ni consulta de agregados (sumas/conteos por periodo, canal, producto o cliente) en Sales.
- `modules/sales/tests/test_boundaries.py` (`main`): un test falla si algún otro módulo importa `modules.sales.*` (`test_only_sales_consumes_the_facades_and_nobody_imports_sales`), y otro si un módulo importa a otro algo distinto de `services.py` (`NON_BUSINESS = {'accounts'}`). **Hoy ese test impediría que Reporting lea Sales por import**; cualquier acceso de Reporting a Sales choca con él tal como está.
- `modules/customers/services.py` y `modules/catalog/services.py` (`main`): fachadas existentes con DTO congelados (`CustomerForSale`, `get_customer_names(ids)`); Sales no tiene `services.py`.

**Patrón de referencia en el backend (`customers`, `catalog`)**
- Estructura `domain/ application/ infrastructure/django/ api/ tests/`: `backend/modules/customers/domain/customer.py:1-80` (dataclass sin Django, validadores que lanzan `CustomerValidationError({campo: [mensaje]})`), `application/commands.py|queries.py` (un caso de uso por clase con `execute`), `infrastructure/django/models.py:6-20` (UUID PK, `created_at/updated_at`, `db_table` explícita), `api/views.py:22-70` (`APIView` delgadas, `_run` traduce errores de dominio a 400/404, filtros por query params, acciones `activate/` y `deactivate/`), `api/pagination.py` propia, `migrations/0001_initial.py`.
- `backend/config/settings/base.py:75-90` — DRF con Token + Session, `IsAuthenticated` global, solo `JSONRenderer`, `PageNumberPagination` con `PAGE_SIZE 50`. `base.py:64-66`: `TIME_ZONE` por entorno, `USE_TZ = True`. No hay roles/permisos por módulo.
- Últimas migraciones: `modules/accounts|catalog|customers/migrations/0001_initial.py` (y `sales/migrations/0001_initial.py` en `main`); `expenses` y `reporting` empezarían en `0001`.

**Frontend (en `main`)**
- `frontend/panel_admin/src/app/app.routes.ts` (`main`): rutas hijas `dashboard` (plantilla), `catalog/products`, `customers`, `sales/orders`, cada una con `loadChildren` a `features/<modulo>/<modulo>.routes.ts`. No hay ruta de gastos ni de reportes.
- `frontend/panel_admin/src/app/dashboard/main/main.component.html` y `.ts` (`main`): el dashboard es **la plantilla Oreva con datos de ejemplo** (tarjetas "New Booking", series "Data 1/Data 2" en `main.component.ts`); no consume ningún endpoint. La plantilla trae `ng-apexcharts`, `ngb-progressbar` y `ngx-scrollbar`, ya importados ahí.
- `frontend/panel_admin/src/assets/data/routes.json` (`main`) define el menú lateral con 4 entradas: Dashboard, Catálogo > Producto, Cliente, Pedidos. `frontend/panel_admin/src/app/layout/sidebar/sidebar-menu.spec.ts:14-40` **fija exactamente 4 rutas y 5 títulos** (`expect(routes.length).toBe(4)`, `titles.length).toBe(5)`) con traducciones en `assets/i18n/{en,es,de}.json`; agregar un menú de Gastos requiere modificar esa prueba.
- Features existentes como patrón: `features/customers/` y `features/products/` (`pages/`, `components/`, `services/`, `models/`, `testing/`, `index.ts`, `*.routes.ts`); `features/sales/` incluye `pipes/money.pipe.ts` y `pages/order-list/order-list-filters.ts` (filtros de lista); `shared/` solo tiene `models/page.ts` y `styles/_table-actions.scss`.

### Hipótesis / supuestos no confirmados
- **Definición de "ingresos considerados"** (REQ-REP-002/005): `ddd.md:706` habla de "Ventas **cobradas**" (base caja: `paid_total`/pagos por `payment_date`), pero REQ-REP-001 pide "ventas" y "pendientes de cobro" por separado y REQ-REP-009 usa "total de ventas / cantidad de pedidos" (base devengado: `total` por `order_date`). Se asume que el requerimiento deja esa definición abierta ("el criterio utilizado debe estar explícito"); no se confirmó con el usuario.
- **Fecha de referencia del periodo** para ventas (¿`order_date`, fecha de entrega `delivered_date` o `payment_date`?) y de pedidos "válidos" (¿todo lo no CANCELLED, o solo DELIVERED/pagados?) no está definida en los REQ. Se asume que "válidos" = no cancelados (REQ-REP-002).
- **Pedidos cancelados con pagos registrados**: `cancel()` los deja con `paid_total > 0`; no hay flujo de reembolso en Sales. No se confirmó si ese dinero cuenta como ingreso en una vista de caja (el TASK de Sales ya lo dejó como duda: `docs/tasks/TASK-ciclo-pedido-entrega-cobro.md:93,133`).
- "**Semana**" del selector de periodo (REQ-REP-001): no se define primer día de semana ni si es "semana en curso" o "últimos 7 días"; la zona horaria efectiva viene de `TIME_ZONE` (no se verificó el valor usado en producción).
- **"Anular o eliminar" (REQ-EXP-004)**: el REQ prefiere anulación lógica "cuando sea necesario conservar trazabilidad"; no se definió si además existe borrado físico, si la anulación pide motivo, ni si un gasto anulado es reversible. `ddd.md:648` nombra `DeleteExpense` y `ddd.md:966` `DELETE /api/expenses/{id}`, lo que podría contradecir "anulación lógica".
- **Campos opcionales de `ddd.md` fuera de los REQ**: `receipt_url` y `ExpenseType` (VARIABLE/FIXED) aparecen en el diseño pero no en ningún REQ-EXP; se asume que quedan fuera del MVP. Tampoco hay REQ de "cierre contable" (`ddd.md:637`).
- **Moneda y signo**: no se verificó la moneda de visualización; `features/sales/pipes/money.pipe.ts` probablemente formatea importes, pero no se leyó su contenido.
- **Dependencias REQ-CUS-004** (usada por REQ-REP-008) se asume cumplida por el módulo Customers existente (historial de compras); no se verificó el id exacto en su TASK.
- Que "pendiente de entrega" excluye CANCELLED y DELIVERED y "pendiente de cobro" usa `balance > 0` con estado no cancelado se infiere de `order.py:250-251` (`can_register_payment`); no se confirmó que sea la regla deseada para las listas del dashboard.

### Módulos y dependencias relacionadas
- **Nuevo bounded context `expenses`** (backend `modules/expenses/` con `domain|application|infrastructure/django|api|tests`, migración `0001`, registro en `INSTALLED_APPS` y `config/urls.py`) y **nuevo `reporting`** (solo lectura). Hoy ninguno existe.
- **Reporting → Sales** y **Reporting → Expenses** (y, para nombres, Customers y Catalog según `ddd.md:766-769`): cruza límites de módulo. Convención vigente: solo vía `services.py` con DTO; el test de límites actual prohíbe que cualquier módulo importe `modules.sales` salvo el propio Sales.
- **Expenses ↔ Sales**: comparten el concepto `PaymentMethod` (vive en `sales/domain/enums.py`); Expenses no debería importar Sales por el mismo límite.
- **Frontend**: nuevas `features/expenses/` y `features/reporting|dashboard`, cambios en `routes.json`, `app.routes.ts`, i18n (`en/es/de`), `sidebar-menu.spec.ts` y reemplazo del contenido de ejemplo de `dashboard/main`.

### Implementaciones similares existentes
- CRUD con activar/desactivar y listado filtrado/paginado: `customers` (`api/views.py:22-70`, `domain/customer.py`, `infrastructure/django/models.py`) y `catalog` — patrón a seguir para categorías de gasto (desactivación sin borrado) y gastos.
- Filtros por rango de fechas, estados y enums parseados con errores por parámetro: `modules/sales/api/filters.py` (`main`) y `OrderFilters` en `domain/repositories.py`.
- Cálculo de totales derivados y dinero en `Decimal` con tope a 12,2: `modules/sales/domain/order.py` (`main`) y `catalog/domain/product.py` (`Decimal`, 2 decimales, `9999999999.99`).
- Fachadas entre módulos: `customers/services.py`, `catalog/services.py` (`main`) y puertos/adaptadores en `sales/application/ports.py`, `sales/infrastructure/adapters.py`.
- Frontend: `features/customers` y `features/sales` (lista con filtros, formulario Reactive Forms, detalle, badges, `money.pipe.ts`, `testing/*-fixtures.ts`); gráficas con `ng-apexcharts` en `dashboard/main`.
- No existe ninguna consulta de agregación en el backend: `git grep -E "Sum\(|aggregate\(|annotate\(|Count\("` sobre `backend/modules` en `main` solo devuelve nombres de tests (`sales/tests/test_repository.py:41,86`), ningún uso del ORM.

### Comportamiento actual
- El usuario autenticado puede gestionar productos, clientes y pedidos (en `main`); **no puede registrar ni ver gastos**, ni hay ningún reporte. El dashboard muestra datos ficticios de la plantilla (`dashboard/main/main.component.html`), sin conexión al backend.
- Las listas de pedidos permiten filtrar por estado, estado de pago, canal, cliente, rango de fechas y `has_balance` (`sales/api/filters.py`, `main`), lo que permite hoy obtener pendientes de entrega/cobro de forma operativa, pero sin totales agregados.
- El importe cobrado está persistido por pedido (`paid_total`), pero los pagos individuales (con `payment_date` y método) solo se leen vía el agregado `Order`/detalle.

### Restricciones
- `CLAUDE.md`: cambios acotados a un objetivo y **plan + confirmación antes de tocar varios archivos**; **dinero siempre `Decimal`**, nunca `float`; nunca editar una migración ya aplicada; no leer ni modificar `.env`; **avisar antes de instalar dependencias** (`pip`/`npm`); dominio sin imports de Django; módulos sin importarse infraestructura entre sí; **Reporting solo lee**; estados cambian por métodos del agregado; serializers validan forma y tipos; no agregar abstracciones DDD sin necesidad real (sección 29); fuera del MVP: microservicios, event sourcing, CQRS completo, inventario/producción avanzados; frontend por `src/app/features/<modulo>/`, servicios inyectables, tipos explícitos sin `any`, Reactive Forms, sin suscripciones colgadas; una rama y un PR por task (`task/TASK-<slug>`), base `main`; PostgreSQL (tests con `DATABASE_URL`, sin SQLite).
- REQ-REP-005 y `ddd.md:709`: etiqueta obligatoria "Ganancia estimada"; no sugerir costo real de producción.
- `test_boundaries.py` (`main`) y la convención de `ddd.md:809`: lectura entre módulos solo por `services.py`.
- Menú lateral cubierto por un test que fija su contenido exacto (`sidebar-menu.spec.ts:14-40`).

### Riesgos identificados
- **Rama desactualizada**: el trabajo de Reporting depende de Sales, que en esta rama no existe; hay que traer `main` (merge) antes de implementar. Si no, no hay contra qué probar REQ-REP-002/006/007/008/009/010.
- **Alcance grande y heterogéneo**: 17 requerimientos en dos bounded contexts nuevos, backend + frontend + migraciones. Riesgo de un PR muy extenso (la regla de una rama/un PR por task obliga a decidir el corte en `delivery-plan`/`delivery-architect`).
- **Definición ambigua de ingreso/ganancia** (ventas cobradas vs. total de pedidos, fecha de referencia, cancelados con pagos): afecta números de dashboard, REQ-REP-005 y la consistencia entre REQ-REP-001/002/009; una mala elección es difícil de cambiar sin recalcular la semántica visible.
- **Acceso de Reporting a Sales**: el límite actual (test + convención `services.py`) no contempla un lector de agregados; hace falta decidir cómo se cruza sin romper "dominio sin Django" y "módulos no se importan infraestructura".
- **Coherencia de totales**: REQ-REP-004 exige que la suma por categoría iguale al total; categorías desactivadas y gastos anulados deben tratarse igual en ambas consultas. Sales persiste importes derivados en `OrderModel`, por lo que las sumas dependen de que esos campos se mantengan consistentes (riesgo de divergencia con el agregado si algún flujo no los actualiza).
- **Husos horarios y límites de periodo**: `USE_TZ=True` y fechas `DateField` en Sales/Expenses; "día/semana/mes" calculados con `TIME_ZONE` pueden desplazar el rango en los bordes.
- **Test de menú rígido** (`sidebar-menu.spec.ts`) y dashboard de plantilla con contenido ficticio: riesgo de dejar datos de ejemplo mezclados con reales si no se reemplaza todo.
- **Sin consultas de agregación existentes** ni `django-filter` (`backend/requirements/base.txt`): cualquier optimización o dependencia nueva requiere avisar antes (`CLAUDE.md`).
- **Posible contradicción del diseño**: `DeleteExpense`/`DELETE /api/expenses/{id}` (`ddd.md:648,966`) frente a "anulación lógica" y "gasto anulado" (REQ-EXP-004).

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — Se crean dos bounded contexts nuevos (`expenses` y `reporting`) con cambios de base de datos (tablas y migraciones de Expenses), y Reporting impacta múltiples módulos (lee Sales y Expenses, y potencialmente Customers y Catalog) lo que obliga a decidir cómo se cruza el límite de módulos hoy bloqueado por `test_boundaries.py`; además hay decisiones estructurales abiertas (definición de ingreso, estado "anulado" frente a borrado, corte del trabajo en PRs).

### Diseño requerido
**SI** — Hay pantallas nuevas (lista y formulario de gastos, gestión de categorías, dashboard real con selector de periodo, indicadores, reportes por categoría/canal/producto/cliente y listas accionables), un nuevo ítem de menú y el reemplazo del dashboard de plantilla; conviene decidir con criterio los componentes de la plantilla Oreva (tarjetas, gráficas, tablas) y la coherencia visual con `features/customers` y `features/sales`.

## Diseño
- [DDR-gastos-reporting-mvp-menu-y-pantallas-gastos](../design/DDR-gastos-reporting-mvp-menu-y-pantallas-gastos.md) — grupo de menú "Gastos ▸ Gastos / Categorías"; lista con filtros de fecha/categoría/estado y total de vigentes; formulario (solo categorías activas, método de pago, categoría inactiva visible al editar); detalle con anulación confirmada (sin botón Eliminar); categorías con alta/edición en diálogo.
- [DDR-gastos-reporting-mvp-dashboard-y-reportes](../design/DDR-gastos-reporting-mvp-dashboard-y-reportes.md) — dashboard real (selector de periodo Hoy/Semana/Mes/Rango, seis indicadores, "Ganancia estimada" rotulada como estimación, pendientes de entrega y de cobro independientes del periodo) y página "Reportes" (ventas por canal, productos, clientes, gastos por categoría).

**Pendiente para `delivery-architect`** (recogido de los DDR): definición de ingresos/ventas considerados y fecha de referencia; semana y zona horaria; si los pendientes dependen del periodo; cómo Reporting lee Sales y Expenses respetando el límite de módulos; anular con `DELETE` o `void/`, reversibilidad y motivo; obligatoriedad de `payment_method`; contrato de listados (total del filtro, paginación) y forma de los endpoints de reportes; corte del trabajo en PRs.

## Arquitectura
**Decisiones de negocio confirmadas por el usuario (2026-10-09):** (1) ventas/ingresos = suma de `total` de pedidos no cancelados, por fecha de pedido (base devengada); (2) los pagos de pedidos cancelados se ignoran en el MVP; (3) anulación de gasto lógica, irreversible y sin motivo (sin `DELETE`); (4) semana = lunes–domingo en curso y los pendientes de entrega/cobro no dependen del periodo.

- [ADR-gastos-reporting-mvp-modelo-dominio-gastos](../adr/ADR-gastos-reporting-mvp-modelo-dominio-gastos.md) — agregados `Expense` y `ExpenseCategory`, `void()` irreversible, `payment_method` propio con default `CASH`, nombre de categoría único sin distinguir mayúsculas, tablas `expenses_*` con `PROTECT`, migración `0001` aditiva, reutiliza `shared/domain/money.py`.
- [ADR-gastos-reporting-mvp-contrato-api-gastos](../adr/ADR-gastos-reporting-mvp-contrato-api-gastos.md) — `/api/expenses/` y `/api/expense-categories/`, `POST …/void/`, filtros, `total_amount` en la lista, errores 400/404/409.
- [ADR-gastos-reporting-mvp-lectura-entre-modulos](../adr/ADR-gastos-reporting-mvp-lectura-entre-modulos.md) — Reporting lee solo por `services.py` (nuevas fachadas de solo lectura en Sales y Expenses), definición única de "pedido válido" y pendientes, módulo `reporting` sin modelos, `test_boundaries.py` pasa a un mapa explícito de dependencias.
- [ADR-gastos-reporting-mvp-contrato-api-reportes](../adr/ADR-gastos-reporting-mvp-contrato-api-reportes.md) — siete rutas `GET /api/reports/*`, resolución de periodo en servidor, ticket promedio `null` sin pedidos, `criteria` único.
- [ADR-gastos-reporting-mvp-frontend-features](../adr/ADR-gastos-reporting-mvp-frontend-features.md) — `features/expenses` y `features/reporting`, `MoneyPipe` y canales a `shared/`, retirada del dashboard de ejemplo, menú a 6 entradas, entrega por fases en un task/PR.

**Para `delivery-plan`:** (a) la rama está detrás de `main` y Sales no existe aquí: la fase 0 es traer `main` (merge); (b) validar el gráfico de dona o usar barra horizontal; (c) fijar el texto exacto de `criteria`; (d) actualizar `ddd.md` (anulación sin `DELETE`, mapa de dependencias, `features/reporting`); (e) decidir si el tamaño del PR obliga a dividir el task entre Gastos y Reporting (opción no adoptada en el ADR de frontend).

## Plan
- [PLAN-2026-10-09-gastos-reporting-mvp](../plans/PLAN-2026-10-09-gastos-reporting-mvp.md) — **v1**, Modo COMPLETO, Specification readiness: **READY**. 28 AC; 5 fases (Expenses backend → Expenses frontend → fachadas de Sales + Reporting backend → Reporting frontend y limpieza → documentación). E2E: NO (humo manual). Sin dependencias nuevas.

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
