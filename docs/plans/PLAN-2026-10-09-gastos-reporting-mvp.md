# PLAN-2026-10-09-gastos-reporting-mvp (v3)

**Task:** TASK-gastos-reporting-mvp
**Modo:** COMPLETO
**DDRs relacionados:** [menú y pantallas de gastos](../design/DDR-gastos-reporting-mvp-menu-y-pantallas-gastos.md), [dashboard y reportes](../design/DDR-gastos-reporting-mvp-dashboard-y-reportes.md)
**ADRs relacionados:** [modelo de dominio de gastos](../adr/ADR-gastos-reporting-mvp-modelo-dominio-gastos.md), [contrato API de gastos](../adr/ADR-gastos-reporting-mvp-contrato-api-gastos.md), [lectura entre módulos](../adr/ADR-gastos-reporting-mvp-lectura-entre-modulos.md), [contrato API de reportes](../adr/ADR-gastos-reporting-mvp-contrato-api-reportes.md), [features frontend](../adr/ADR-gastos-reporting-mvp-frontend-features.md)
**Specification readiness:** READY

## Objective
Registrar y clasificar las salidas de dinero (REQ-EXP-001 a 007) y mostrar un dashboard y reportes de ventas y gastos por periodo (REQ-REP-001 a 010), para entender en qué se gasta y cuál es la ganancia estimada. Alcance: dos módulos nuevos (`expenses`, `reporting`), nuevas fachadas de solo lectura en `sales`, dos features Angular y la retirada del dashboard de ejemplo.

## Context
Investigación, DDR y ADR en `docs/tasks/TASK-gastos-reporting-mvp.md`. Verificado contra `origin/main` (`f7af20f`) al planificar: la rama `task/TASK-gastos-reporting-mvp` parte de ahí, por lo que **Sales ya existe** (la fase 0 del ADR de frontend —traer `main`— queda resuelta). Sigue vigente: `backend/modules/` tiene `accounts, catalog, customers, sales` (sin `expenses` ni `reporting`); `backend/shared/domain/money.py` existe (`parse_money`, `MONEY_MAX`, `InvalidMoney`); `config/settings/base.py:10-25` registra hasta `modules.sales`; `modules/sales/models.py` reexporta modelos desde `infrastructure/django/models.py`; los módulos usan `_run` con `transaction.atomic()` + `get_for_update` (`sales/api/views.py:63-80`); `SystemClock` (`sales/infrastructure/adapters.py`) usa `timezone.localdate()`; `features/<modulo>/index.ts` expone la API pública de la feature; `shared/` tiene `models/page.ts` y `styles/_table-actions.scss`; `package.json` no incluye Playwright.

Decisiones de negocio confirmadas por el usuario (2026-10-09): ventas = suma de `total` de pedidos no cancelados por fecha de pedido; pagos de pedidos cancelados ignorados en el MVP; anulación de gasto lógica, irreversible y sin motivo; semana lunes–domingo y pendientes independientes del periodo.

# Specification

## Domain context
**Bounded Contexts:** Expenses (nuevo, dueño de gastos y categorías) y Reporting (nuevo, solo lectura).
**Related contexts:** Sales (fuente de ventas y pendientes, solo vía `modules/sales/services.py`), Customers (nombres vía `customers.services.get_customer_names`). Catalog no se usa (los nombres de producto son los snapshots de los ítems). Dependencias permitidas: `reporting → {sales, expenses, customers}`, `sales → {catalog, customers}`; Expenses no importa módulos.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Gasto (`Expense`) | Salida de dinero registrada: descripción, monto, categoría, fecha, método de pago, proveedor y notas opcionales | REQ-EXP-002, ADR dominio |
| Categoría de gasto (`ExpenseCategory`) | Clasificación del gasto; activa o inactiva; nunca se borra | REQ-EXP-001/006 |
| Vigente / Anulado (`ACTIVE` / `VOIDED`) | Estado del **gasto**; anular es irreversible y quita el gasto de los totales | REQ-EXP-004, usuario |
| Cancelado | Estado del **pedido** (`CANCELLED`); distinto de "anulado" (gasto) e "inactiva" (categoría) | `sales/domain/enums.py` |
| Pedido válido | Pedido no cancelado y con al menos un ítem; es la base de toda métrica de ventas | ADR lectura, usuario |
| Ventas del periodo | Σ `total` de pedidos válidos con `order_date` en el rango; **no es lo cobrado** | usuario |
| Pendiente de entrega | Pedido válido en `NEW`, `IN_PREPARATION` o `READY` | REQ-REP-010, ADR lectura |
| Pendiente de cobro | Pedido válido con `total − paid_total > 0`, en cualquier estado logístico | REQ-REP-010, ADR lectura |
| Ganancia estimada | `ventas − gastos vigentes` del periodo; estimación, sin costo de producción | REQ-REP-005 |
| Venta directa | Texto de UI para el canal `STORE` | `sales` frontend (`SALES_CHANNEL_LABELS`) |

**Inconsistencias declaradas (no se resuelven por inferencia):** (1) `ddd.md:706` dice "Ventas cobradas − Gastos"; el usuario decidió base devengada, por lo que `ddd.md` debe corregirse (AC-28). (2) `ddd.md:648,966` prevé `DeleteExpense`/`DELETE`; se reemplaza por anulación lógica. (3) `ddd.md:1084` nombra `features/dashboard/`; se usa `features/reporting/`. (4) REQ-REP-005 habla de "ingresos/gastos del periodo"; aquí "ingresos" = ventas devengadas, y los pagos no intervienen.

## Current behavior
No hay gastos, categorías ni reportes (`backend/modules/` sin `expenses`/`reporting`; `config/urls.py` sin `api/expenses/`, `api/expense-categories/`, `api/reports/`). El dashboard (`frontend/panel_admin/src/app/dashboard/main/`) es la plantilla con datos de ejemplo. Sales persiste `total`, `paid_total`, `status`, `payment_status`, `sales_channel`, `order_date`, `customer_id` (`sales/infrastructure/django/models.py`) y no tiene consultas de agregación ni `services.py`. `test_boundaries.py` prohíbe que cualquier módulo importe `modules.sales`. El menú tiene 4 entradas (`assets/data/routes.json`, `sidebar-menu.spec.ts`).

## Expected behavior
**Expenses.** El usuario crea y gestiona categorías; registra gastos con descripción, monto > 0, categoría activa, fecha, método de pago (por omisión efectivo), y proveedor y notas opcionales; edita, anula y lista gastos con filtros por rango de fechas, categoría y estado. Un gasto anulado deja de sumar en cualquier total. Una categoría desactivada no se ofrece para gastos nuevos, pero sus gastos históricos la conservan.
**Reporting.** Para un periodo (día, semana lunes–domingo, mes o rango) el sistema entrega ventas, cantidad de pedidos, ticket promedio, gastos totales y por categoría, ganancia estimada, ventas por canal, productos más vendidos y clientes con mayor compra; y, sin depender del periodo, las listas de pedidos pendientes de entrega y de cobro. Todo se obtiene leyendo Sales y Expenses sin modificarlos.

## Domain rules / invariants
**Existentes (deben seguir verdaderas):** dinero en `Decimal` con 2 decimales, nunca `float`; los estados cambian por métodos del agregado; los módulos solo se leen por `services.py`; Reporting no modifica nada; `Order.cancel` no toca pagos.
**Nuevas:**
- INV-01: `Expense.amount > 0` y ≤ `MONEY_MAX`; `float`/`bool` rechazados (`parse_money`).
- INV-02: descripción obligatoria (máx. 200), fecha obligatoria, categoría obligatoria; proveedor máx. 150, notas máx. 2000.
- INV-03: `payment_method` ∈ {`CASH`,`QR`,`BANK_TRANSFER`,`CARD`,`OTHER`}; omitido → `CASH`.
- INV-04: al crear, la categoría existe y está activa; al editar, se puede conservar la actual aunque esté inactiva, pero cambiar a otra exige que esté activa.
- INV-05: `Expense.void(now)` pasa `ACTIVE → VOIDED` y fija `voided_at`; es irreversible; anular de nuevo o editar un gasto anulado es una violación de regla. No hay borrado físico de gastos ni de categorías (`PROTECT` en la FK).
- INV-06: nombre de categoría obligatorio, recortado, máx. 100, único sin distinguir mayúsculas.
- INV-07: todo total de gastos suma solo gastos `ACTIVE`; el total por categorías es la suma de sus filas (misma consulta).
- INV-08: pedido válido = `status ≠ CANCELLED` y ≥ 1 ítem; ventas y conteo salen solo de pedidos válidos con `order_date` en el rango inclusivo; los pagos no intervienen.
- INV-09: `estimated_profit = sales_total − expenses_total` (puede ser negativo); `average_ticket = sales_total / orders_count`, o `null` si `orders_count = 0`.
- INV-10: los pendientes no dependen del periodo.

## Acceptance criteria
**Backend — Expenses**
- AC-01: Crear una categoría con nombre válido devuelve 201 y aparece en `GET /api/expense-categories/?active=true`; sin nombre → 400 en `name`; el mismo nombre en otras mayúsculas → 400 en `name`.
- AC-02: Renombrar, desactivar y activar una categoría funcionan; desactivarla no cambia sus gastos; no existe `DELETE` (405).
- AC-03: Un gasto válido se registra (201), se devuelve con su categoría embebida y aparece en `GET /api/expenses/` con el filtro de su fecha.
- AC-04: Monto 0, negativo, con más de 2 decimales, no numérico o escrito con notación científica o separadores (`1e3`, `1_000`) → 400 en `amount`; descripción, fecha o categoría faltantes → 400 en su campo; los errores se acumulan por campo.
- AC-05: Registrar con categoría inexistente o inactiva → 400 en `category_id`; editar un gasto conservando su categoría ya inactiva se acepta; cambiarlo a una categoría inactiva → 400.
- AC-06: `PATCH` con monto, categoría o fecha actualiza el gasto con las mismas validaciones, y las consultas y totales posteriores lo reflejan.
- AC-07: `POST …/void/` deja el gasto `VOIDED` con `voided_at`; deja de sumar en `total_amount` y en los reportes; repetirlo → 409 `already_voided`; `PATCH` sobre un anulado → 409 `expense_voided`; `DELETE` → 405.
- AC-08: `GET /api/expenses/` filtra por `date_from`/`date_to` inclusive y `category_id`; `status` por omisión `active` (`voided`, `all` disponibles); orden `-expense_date`; incluye `total_amount` (suma de vigentes de todas las páginas que cumplen fecha y categoría, independiente de `status`); parámetros inválidos → 400 por parámetro.
- AC-09: `payment_method` acepta los cinco valores, omitido queda `CASH`, uno inválido → 400; el detalle lo devuelve.
**Backend — Reporting**
- AC-10: `GET /api/reports/sales/` devuelve `total` y `orders_count` de pedidos válidos del rango (inclusivo, por `order_date`); un pedido cancelado o sin ítems no cuenta; los pagos no cambian el resultado.
- AC-11: `GET /api/reports/expenses/` suma solo gastos vigentes del rango, desglosa por categoría (incluidas inactivas con monto > 0) y `Σ categories[].total == total`; un gasto anulado no aparece.
- AC-12: `GET /api/reports/dashboard/` devuelve `estimated_profit = sales_total − expenses_total` (negativo permitido), el criterio de ventas, y los contadores de pendientes.
- AC-13: `average_ticket` es `total / pedidos`; con 0 pedidos es `null` y la respuesta es 200 con ceros.
- AC-14: `period=day|week|month` o `date_from`+`date_to`; `week` es lunes–domingo de la semana en curso (fecha local con `TIME_ZONE`); por omisión `month`; `period` junto con fechas, solo una fecha, o `date_from > date_to` → 400; toda respuesta con periodo incluye `period.{kind,date_from,date_to}`.
- AC-15: `sales-by-channel` agrupa pedidos válidos por canal, orden `total` desc.
- AC-16: `top-products` agrupa ítems de pedidos válidos por `product_id` con `units` y `amount` (antes de descuento) y el nombre del snapshot más reciente; orden `units` desc, `amount` desc, nombre; máximo 10.
- AC-17: `top-customers` rankea clientes (no nulos) de pedidos válidos por `total` desc, `orders_count` desc; incluye nombre vigente; máximo 10; excluye pedidos sin cliente.
- AC-18: `pending` devuelve `delivery` (válidos en NEW/IN_PREPARATION/READY, orden por entrega prevista asc con nulos al final y luego `order_date`) y `collection` (válidos con saldo > 0, orden `order_date` asc), con `count`, `balance_total` en cobro y hasta 10 filas; un pedido `DELIVERED` y `PARTIAL` aparece solo en cobro; cancelados no aparecen; no depende del periodo.
- AC-19: Las rutas de gastos y reportes exigen autenticación (401 sin token); `test_boundaries.py` verifica el mapa de dependencias permitido (solo vía `services`), que nadie importa `modules.reporting`, y que Expenses no importa módulos de negocio.
**Frontend**
- AC-20: El menú tiene 6 entradas (Dashboard, Catálogo, Cliente, Pedidos, Gastos ▸ Gastos/Categorías, Reportes) con traducciones `en/es/de`, y `sidebar-menu.spec.ts` lo refleja.
- AC-21: La lista de gastos muestra filtros (Desde, Hasta, Categoría, Estado con "Vigentes" por omisión) y atajos (Este mes por omisión, Mes anterior, Todo), columnas del DDR, el total del filtro tomado de `total_amount`, anulados atenuados sin acciones, y estados de carga/vacío/error.
- AC-22: El formulario de gasto (crear/editar) valida en cliente (monto > 0, campos obligatorios), fecha = hoy y método = Efectivo por omisión, ofrece solo categorías activas (más la actual "(inactiva)" al editar), bloquea Guardar sin categorías activas con enlace a Categorías, muestra errores del servidor bajo su campo y redirige un gasto anulado al detalle.
- AC-23: El detalle muestra todos los datos (incluido método de pago y "(inactiva)" si corresponde) y "Anular gasto" con confirmación; un anulado muestra el badge y oculta Editar/Anular.
- AC-24: La pantalla de categorías lista (filtro Activas por omisión), crea y edita en diálogo, activa/desactiva con confirmación, y no ofrece eliminar.
- AC-25: El dashboard reemplaza el contenido de ejemplo: selector de periodo común, seis indicadores, tarjeta titulada "Ganancia estimada" con la nota de estimación y la fórmula, ticket promedio "—" sin pedidos, tablas de pendientes (máx. 10, enlaces a pedidos y "Ver todos" con el atajo de Pedidos) con la nota "Estado actual, no depende del periodo", y cada tarjeta carga/falla y reintenta de forma independiente.
- AC-26: La página Reportes ofrece el mismo selector, los totales de ventas y gastos con el criterio visible, ventas por canal, productos más vendidos (con aviso de importes antes de descuento), clientes con mayor compra (con aviso de pedidos sin cliente) y gastos por categoría con total coincidente; estado vacío por tarjeta.
- AC-27: `MoneyPipe` y las etiquetas/lista de canales viven en `shared/`; las pantallas y pruebas de Sales siguen pasando sin cambios de comportamiento.
**Documentación**
- AC-28: `docs/architecture/ddd.md` refleja anulación sin `DELETE`, base devengada de la ganancia, mapa de dependencias por `services.py`, fachadas de Sales/Expenses y `features/reporting`.

## Edge cases
- EDGE-01: Gasto con monto `0.001`, `1e3`, `1E3`, `1_000`, `"abc"`, `true` o `10000000000.00` → 400 en `amount`. Un monto inválido no oculta los errores de los demás campos: `{amount: "abc", description: ""}` → 400 con `amount`, `description`, `category_id` y `expense_date` a la vez.
- EDGE-02: Rango con un solo día (`date_from == date_to`) incluye ese día; gastos y pedidos en los bordes cuentan.
- EDGE-03: Sin gastos o sin pedidos: totales `"0.00"`, listas vacías, `average_ticket = null`, 200 (nunca 404/500).
- EDGE-04: Ganancia negativa (gastos > ventas) se devuelve con signo.
- EDGE-05: Pedido sin ítems, o con total 0 pero con ítems (precio 0 permitido por Sales), distingue: el primero no es válido, el segundo sí.
- EDGE-06: Pedido cancelado con `paid_total > 0` no suma ventas ni aparece como pendiente de cobro.
- EDGE-07: Pedido `DELIVERED` + `PARTIAL` (saldo > 0) está solo en cobro; `READY` + `PAID` solo en entrega; `DELIVERED` + `PAID` en ninguna.
- EDGE-08: Categoría desactivada con gastos del periodo sigue en el desglose; una categoría activa sin gastos del periodo no aparece.
- EDGE-09: Categoría con nombre `" Empaque "` y otra `"empaque"` colisionan (recorte + sin distinguir mayúsculas).
- EDGE-10: Dos `void` concurrentes sobre el mismo gasto: uno gana, el otro recibe 409 (`get_for_update`).
- EDGE-11: `week` calculado un lunes y un domingo; `month` en febrero bisiesto y en fin de año.
- EDGE-12: Ranking con empates se ordena de forma determinista (criterios de desempate del AC).
- EDGE-13: Un cliente del ranking que ya no existe en Customers → se omite su nombre con valor vacío sin fallar.
- EDGE-14: Mismo producto con nombres distintos en snapshots → un solo renglón con el nombre más reciente.

## Error cases
400 por validación de campo y de parámetros (`{campo: [mensajes]}`); 404 `{detail}` con id inexistente o mal formado; 409 `{detail, code}` para `already_voided` y `expense_voided`; 405 para `DELETE`; 401 sin autenticación. Ante falla de red/500 en el frontend: mensaje con "Reintentar" por tarjeta (no vacía la pantalla).

## Authorization / permissions
Sin roles en el sistema: `IsAuthenticated` global (`config/settings/base.py:75-90`), todas las rutas nuevas heredan ese comportamiento; Reporting es de solo lectura (solo `GET`). El frontend no es la barrera de seguridad.

## API contract
Detallado en [contrato de gastos](../adr/ADR-gastos-reporting-mvp-contrato-api-gastos.md) y [contrato de reportes](../adr/ADR-gastos-reporting-mvp-contrato-api-reportes.md); no cambia ninguna ruta existente.
- API-01: `GET|POST /api/expenses/`, `GET|PATCH /api/expenses/{id}/`, `POST /api/expenses/{id}/void/`.
- API-02: `GET|POST /api/expense-categories/`, `GET|PATCH /api/expense-categories/{id}/`, `POST …/activate/` y `…/deactivate/`.
- API-03: `GET /api/reports/{dashboard,sales,expenses,sales-by-channel,top-products,top-customers,pending}/`.
- API-04: Importes como cadena de 2 decimales; ids UUID como cadena; fechas ISO `AAAA-MM-DD`.
- **Texto del criterio de ventas** (lo fija este plan, texto fijo y único en `reporting/application`): `"Ventas: total de los pedidos no cancelados con al menos un producto, según su fecha de pedido. No equivale a lo cobrado. La ganancia estimada no incluye costo de producción."`

## UI behavior
Derivado de los DDR sin cambios (menú, lista, formulario, detalle, categorías en `NgbModal`, selector de periodo, tarjetas de indicador, tablas de pendientes, reportes). Estados: `loadingIndicator`/spinner por tarjeta, vacío con mensaje, error con `toastr` o con "Reintentar", Guardar deshabilitado si inválido o enviando. Textos de pantalla en español; el menú pasa por `translate`.
- UI-01: Importes con `MoneyPipe` ("Bs 70.00"); fechas `dd/MM/yyyy`.
- UI-02: Gasto anulado atenuado, monto tachado, sin Editar/Anular.
- UI-03: Ganancia ≥ 0 en verde, < 0 en rojo; rótulo literal "Ganancia estimada"; la pantalla no afirma ni insinúa costo de producción, margen ni utilidad contable: esas palabras solo pueden aparecer para negarlas (la nota fija del dashboard y el criterio de ventas de API-04).

## Non-functional requirements
- Precisión: `Decimal` en dominio, agregaciones y serialización; nunca `float`.
- Rendimiento: agregaciones en SQL (`Sum`/`Count` con `values().annotate()`), nombres de clientes en una consulta por lote; sin N+1; los pendientes con límite 10.
- Concurrencia: `update` y `void` con `get_for_update` dentro de `transaction.atomic()`.
- Compatibilidad: sin cambios de contrato en Sales/Customers/Catalog; los cambios en Sales son aditivos (`services.py`, `read_queries.py`) más un movimiento mecánico en frontend.

## Out of scope
`receipt_url`, `ExpenseType`, cierre contable, borrado físico, reversión o motivo de anulación, creación rápida de categoría desde el formulario de gasto, exportación, comparación entre periodos, tendencia mensual, reporte de rentabilidad aparte, cobro por caja (pagos) como ingreso, reembolsos, roles/permisos, internacionalización del contenido de pantallas, dividir el task en dos.

## Open questions
No bloqueantes: (1) si la dona de ApexCharts no es viable en la plantilla se usa barra horizontal (decidido en el ADR de frontend; se valida en la fase 4); (2) el volumen real de datos no se midió, por lo que no se añaden índices compuestos más allá de los de los ADR.

# Test Specification

## Unit tests
- Dominio de Expenses (`SimpleTestCase`, sin base de datos): `Expense.create/update/void` y `ExpenseCategory.create/rename/activate/deactivate` cubren INV-01 a 06 y EDGE-01, 09; acumulación de errores por campo. v2: EDGE-01 con `1e3`, `1E3`, `1_000`, `' 1e3 '`, `+5` y `1e-7`; un monto no numérico con otros campos inválidos acumula todos los errores.
- Dominio de Reporting: `Period` (día, semana lunes–domingo, mes, rango y validaciones) con EDGE-02 y EDGE-11; fórmulas de ganancia y ticket (INV-09, EDGE-03/04) con fakes de los puertos.
- Frontend: servicios de API (mapeo DTO↔modelo, errores), validadores y mapeo de filtros de la lista de gastos, lógica del selector de periodo, formateo del `MoneyPipe` ya en `shared/`.

## Integration tests
- Backend (Django `TestCase` sobre PostgreSQL, DRF `APIClient` autenticado con token): AC-01 a 09 (API de gastos y categorías, incluidos 400/404/405/409, `total_amount`, EDGE-08/10); AC-10 a 18 (API de reportes con pedidos creados mediante el agregado `Order` y el repositorio de Sales, no por ORM directo, para que `total`/`paid_total` sean los reales; EDGE-05/06/07/12/13/14); AC-19 (401 sin token).
- Repositorios: `DjangoExpenseRepository` y `DjangoExpenseCategoryRepository` (guardar/leer, restricciones: monto > 0, nombre único sin distinguir mayúsculas, `PROTECT`).
- Fachadas: `modules/sales/tests/test_services.py` (cada función contra pedidos reales) y `modules/expenses/tests/test_services.py` (suma de filas = total).
- Límites: `test_boundaries.py` reescrito con el mapa permitido (AC-19), ejecutado en `SimpleTestCase`.
- Frontend (Karma + `TestBed` + `HttpTestingController`): componentes de lista, formulario, detalle y categorías de gastos; dashboard y reportes (carga independiente, error con "Reintentar", estados vacíos, ticket "—", ganancia con etiqueta y nota); `period-selector`; `sidebar-menu.spec.ts` (6 rutas, 9 títulos, traducciones).

## E2E
**¿Corresponde E2E?** NO. No hay Playwright en `frontend/panel_admin/package.json` y los cinco flujos se validan con pruebas de API de punta a punta en backend (incluida la composición con Sales) más pruebas de componente con `HttpTestingController` en frontend; instalar Playwright sería una dependencia nueva que ningún flujo exige. Como en las tareas anteriores, `delivery-engineer` hace un **humo manual** con el backend y `npm start`: crear categoría, registrar/editar/anular un gasto, ver el dashboard y Reportes con un pedido real.

## Regression tests
- Suites completas existentes de `accounts`, `catalog`, `customers`, `sales` (`python manage.py test`) y de frontend (`npm test`, `npm run lint`) deben seguir en verde.
- Específicas: pantallas de Sales tras mover `MoneyPipe`/canales a `shared/` (`order-*.spec.ts`), `sidebar-menu.spec.ts`, y el `test_boundaries.py` reemplazado (que incluya aún las comprobaciones originales de que `sales` solo usa `services` de `catalog`/`customers`).

## Acceptance criteria mapping
| AC | Verificación |
|---|---|
| AC-01, 02 | Integración API de categorías; unit del dominio de categoría; repositorio (unicidad ci) |
| AC-03, 04 | Integración API + unit del dominio de gasto |
| AC-05 | Integración API (crear/editar con categorías activa/inactiva) + unit de la regla de aplicación |
| AC-06 | Integración API (editar y verificar `/reports/expenses/`) |
| AC-07 | Integración API (void, 409, 405) + unit de `void()` + concurrencia (EDGE-10) |
| AC-08 | Integración API (filtros, `status`, `total_amount`, 400) |
| AC-09 | Integración API + unit del enum |
| AC-10, 13 | Integración API de reportes con pedidos reales + unit de fórmulas |
| AC-11 | Integración API + prueba de coherencia Σ categorías = total |
| AC-12 | Integración API (`dashboard`) + unit de la composición con fakes |
| AC-14 | Unit de `Period` + integración (400 por combinaciones) |
| AC-15, 16, 17 | Integración API sobre fachadas de Sales (`test_services.py`) |
| AC-18 | Integración API + `test_services.py` de Sales (EDGE-05/06/07) |
| AC-19 | Integración (401) + `test_boundaries.py` |
| AC-20 | Angular `sidebar-menu.spec.ts` |
| AC-21 a 24 | Angular `TestBed` de las páginas/diálogo de Gastos |
| AC-25, 26 | Angular `TestBed` de dashboard y reportes + `period-selector.spec.ts` + humo manual |
| AC-27 | Specs de Sales existentes tras el movimiento + `npm run build` |
| AC-28 | Revisión del diff de `ddd.md` |

# Implementation Plan

## Architecture considerations
Se cumplen los ADR sin reabrirlos: Expenses sigue el patrón `domain/ application/ infrastructure/django/ api/` de Customers/Sales; Reporting no tiene modelos y compone puertos sobre las fachadas `services.py` (Sales, Expenses, Customers); las agregaciones viven en `sales/infrastructure/django/read_queries.py` y en el repositorio de Expenses, nunca en Reporting; `shared/domain/money.py` se reutiliza sin modificarlo. Sin migraciones en Reporting ni en Sales. No hay conflicto con `ddd.md`: se corrige donde difiere (AC-28). Dinero siempre `Decimal`.

## Proposed solution
Cinco fases con commits separados dentro de un solo task y PR; cada fase deja las suites en verde.

## Files/components affected
- **Backend (nuevo) `backend/modules/expenses/`:** `__init__.py`, `apps.py`, `models.py` (reexporta), `services.py`; `domain/{__init__,category,expense,enums,exceptions,repositories}.py`; `application/{__init__,commands,queries,ports,exceptions?}.py`; `infrastructure/{__init__}.py`, `infrastructure/django/{__init__,models,mappers,repositories}.py`; `api/{__init__,urls,views,serializers,filters,pagination}.py`; `migrations/{__init__,0001_initial}.py`; `tests/{__init__,test_domain,test_application,test_repository,test_api,test_services}.py` y `fakes.py`.
- **Backend (nuevo) `backend/modules/reporting/`:** `__init__.py`, `apps.py`; `domain/{__init__,period}.py`; `application/{__init__,ports,queries,criteria}.py`; `infrastructure/{__init__,adapters}.py`; `api/{__init__,urls,views,serializers,params}.py`; `tests/{__init__,fakes,test_domain,test_application,test_api}.py`.
- **Backend (modificado):** `modules/sales/services.py` (nuevo), `modules/sales/infrastructure/django/read_queries.py` (nuevo), `modules/sales/tests/test_services.py` (nuevo), `modules/sales/tests/test_boundaries.py` (reescrito); `config/settings/base.py` (`modules.expenses`, `modules.reporting`); `config/urls.py` (`api/expenses/`, `api/expense-categories/`, `api/reports/`).
- **Frontend (nuevo):** `src/app/features/expenses/**` y `src/app/features/reporting/**` (estructura del ADR de frontend); `src/app/shared/pipes/money.pipe.ts`, `src/app/shared/models/sales-channel.ts`.
- **Frontend (modificado):** `app.routes.ts` (rutas `expenses`, `reports`), `dashboard/dashboard.routes.ts` (`main` → página de `features/reporting`), eliminación de `dashboard/main/*`, `assets/data/routes.json`, `assets/i18n/{en,es,de}.json`, `layout/sidebar/sidebar-menu.spec.ts`, imports de `MoneyPipe` y canales en `features/sales/**`.
- **Documentación:** `docs/architecture/ddd.md`, TASK y este plan.

## Implementation steps

**Fase 0 — Línea base.** Rama `task/TASK-gastos-reporting-mvp` creada desde `origin/main` (hecho al planificar). Antes de codificar, correr `python manage.py test` y `npm test` para fijar la base verde. (Resuelve el riesgo "rama atrás de main".)

**Fase 1 — Backend Expenses (AC-01 a 09, INV-01 a 06, AC-19 parcial).**
1. `domain/enums.py` (`ExpenseStatus`, `PaymentMethod`), `domain/exceptions.py` (`ExpenseValidationError`, `ExpenseRuleViolation`, `ExpenseNotFound`, `ExpenseCategoryNotFound`), `domain/category.py` y `domain/expense.py` (con `UNSET`, `parse_money`, `void(now)`), `domain/repositories.py` (`ExpenseFilters`, `ExpenseSummary`, interfaces). Tests de dominio primero (INV-01 a 06, EDGE-01, 09).
2. `application/ports.py` (`Clock`), `application/commands.py` y `queries.py` (casos de uso del ADR; regla de categoría activa/conservada en `CreateExpense`/`UpdateExpense`; unicidad ci en categorías). Tests de aplicación con fakes (AC-05).
3. `infrastructure/django/{models,mappers,repositories}.py` y `models.py`/`apps.py`; registrar en `INSTALLED_APPS`; `makemigrations expenses` → `0001_initial` (restricciones del ADR); tests de repositorio contra PostgreSQL.
4. `api/`: `serializers.py` (forma/tipos, `DecimalField(12,2)`), `filters.py` (`parse_expense_filters`: `date_from`, `date_to`, `category_id`, `status`), `pagination.py` (`ExpensePagination` con `total_amount`; la agregación la entrega el repositorio/consulta para que cubra todas las páginas), `views.py` (`_run` con `transaction.atomic()`; 400/404/409; `DELETE` → 405), `urls.py`; montar en `config/urls.py`. Tests de API (AC-01 a 09, EDGE-10, 401).
5. `services.py`: `get_expense_report(date_from, date_to)` y DTOs (`ExpenseReport`, `CategoryExpense`); `test_services.py` (AC-11, INV-07).

**Fase 2 — Frontend Expenses (AC-20 parcial, AC-21 a 24).**
6. Modelos y servicios (`expense.ts`, `category.ts`, `expenses-api.service.ts`, `categories-api.service.ts`) con mapeo DTO↔modelo y manejo de errores como en `customers-api.service.ts`; fixtures de prueba.
7. Páginas `expense-list` (filtros, atajos, `total_amount`), `expense-form`, `expense-detail` (anular con `Swal`) y `category-list` + `category-dialog` (`NgbModal`); rutas `expenses.routes.ts` y `loadChildren` en `app.routes.ts`; specs.
8. Menú: `routes.json` (grupo Gastos ▸ Gastos/Categorías), i18n `en/es/de` y `sidebar-menu.spec.ts` en el estado intermedio (5 entradas); `npm test`, `npm run lint`, `npm run build`.

**Fase 3 — Fachadas de Sales y Backend Reporting (AC-10 a 19, INV-08 a 10).**
9. `modules/sales/infrastructure/django/read_queries.py` y `modules/sales/services.py` con las seis funciones y DTOs del ADR (pedido válido = no cancelado + ≥ 1 ítem; periodos inclusivos; productos con nombre del ítem más reciente; clientes no nulos; pendientes con límite). `test_services.py` con pedidos reales (EDGE-05/06/07/12/14).
10. Reescribir `test_boundaries.py` con el mapa permitido; asegurar que las comprobaciones originales siguen incluidas.
11. `modules/reporting/`: `domain/period.py` (`Period`, resolución de `day|week|month|range`, validaciones); `application/ports.py`, `criteria.py` (texto fijo de API-04) y `queries.py` (siete casos de uso con la composición de INV-09); `infrastructure/adapters.py` (solo `services` de Sales, Expenses y Customers; `SystemClock` con `timezone.localdate()`); `api/` (`params.py` para `period`/fechas con 400 por parámetro, serializers de cadena `Decimal`, vistas `GET`, `urls.py`); registrar app y montar `api/reports/`. Tests de dominio, de aplicación con fakes y de API (AC-10 a 18).

**Fase 4 — Frontend Reporting y limpieza (AC-20, 25, 26, 27).**
12. Mover `MoneyPipe` y `SalesChannel`/`SALES_CHANNELS`/`SALES_CHANNEL_LABELS` a `shared/`; actualizar imports de Sales (re-exportar el modelo de canal desde `features/sales/models/order.ts` si hay pruebas que lo importan); ejecutar las specs de Sales antes y después (AC-27).
13. `features/reporting`: `report.ts`, `reporting-api.service.ts`, `period-selector`, `kpi-card`, tablas de ranking/pendientes, `dashboard` y `reports` con estado `loading|error|data` por tarjeta. Validar el tipo `donut` de `ng-apexcharts` (comprobar que el paquete lo soporta y renderiza en una prueba o en el humo manual); si no es viable, usar barra horizontal con el mismo layout.
14. Enrutar `dashboard/main` a la página de `features/reporting`, borrar `dashboard/main/*`, añadir `reports` a `app.routes.ts`, entrada de menú "Reportes", i18n y `sidebar-menu.spec.ts` final (6 rutas, 9 títulos); specs de dashboard, reportes y selector.
15. `npm test`, `npm run lint`, `npm run build`; humo manual (backend + `npm start`): categoría → gasto → editar → anular → dashboard y Reportes con un pedido real; registrar el resultado en `## Implementación`.

**Fase 6 — Correcciones del review (REV-2026-10-09-gastos-reporting-mvp-01).**
17. `modules/expenses/domain/validation.py`: `positive_money` rechaza (error en `amount`) los textos que no sean un decimal plano (`^\d+(\.\d+)?$` tras recortar espacios): notación científica, `_`, signo y separadores. Los `Decimal`/`int` siguen pasando por `parse_money`. No se modifica `shared/domain/money.py` (su endurecimiento afectaría a Catalog y Sales; fuera de alcance). (AC-04, EDGE-01, INV-01)
18. `modules/expenses/api/serializers.py`: `amount` pasa de `DecimalField` a `CharField` (forma y tipo; los números JSON se aceptan como texto) para que el dominio valide y acumule los errores de todos los campos. El contrato y la representación de salida (`"120.50"`) no cambian. (AC-04, API-01)
19. Tests: dominio y API con los casos de EDGE-01 ampliados y el caso de errores acumulados; verificar que `1000`, `"10"`, `"120.5"` y `12.5` siguen aceptándose.
20. REV-02 no requiere código: UI-03 queda reformulado en esta versión.

**Fase 5 — Documentación (AC-28).**
16. Actualizar `ddd.md` (secciones 7, 8, 10 y endpoints/estructura): anulación lógica sin `DELETE`, ganancia por ventas devengadas, mapa de dependencias por `services.py` y fachadas existentes, `features/reporting`. Actualizar el TASK.

## Database / migrations
Una migración nueva: `modules/expenses/migrations/0001_initial.py` (generada con `makemigrations`; solo crea `expenses_category` y `expenses_expense`; reversible con `migrate expenses zero`). Sin migraciones en Sales ni Reporting. Sin datos que migrar ni backfill. Nunca editar `0001` una vez aplicada. Rollback en producción: quitar los `include` de rutas y conservar las tablas si ya hay gastos.

## Risks
- **PR grande (5 fases, 17 REQ):** mitigado con commits por fase y suites verdes en cada una; el corte natural, si el review lo exige, es tras la fase 2 (decisión del usuario; implica dividir el task).
- **Agregaciones sobre columnas derivadas de Sales:** dependen de que `total` esté bien persistido; se prueba creando pedidos por el agregado (no por ORM directo) y se reutiliza la prueba de coherencia existente.
- **Reescribir `test_boundaries.py`:** podría debilitar el límite; se mantiene todo lo comprobado antes y se añade el mapa explícito.
- **Dona de ApexCharts no verificada:** respaldo definido (barra horizontal); no bloquea ninguna AC.
- **Mover `MoneyPipe`/canales:** toca Sales; commit propio y specs de Sales antes/después.
- **Husos horarios:** `week`/`day` usan `timezone.localdate()`; las pruebas fijan la fecha con el reloj inyectado, no con la hora del sistema.
- **Importes de producto antes de descuento:** pueden sumar más que las ventas; mitigado con el aviso en la UI (AC-26).

## New dependencies
Ninguna (backend: Django/DRF/psycopg existentes; frontend: `ng-apexcharts`, `@ng-bootstrap/ng-bootstrap`, `@ng-select/ng-select`, `ngx-datatable`, `sweetalert2`, `ngx-toastr` ya instalados). No se instala Playwright ni librería de datepicker.

## Changelog
- **v2** (2026-10-09): [Implementation Plan] Se agrega la fase 6 para rechazar montos con notación científica o separadores y acumular los errores del dominio (EDGE-01, AC-04 se verifican con casos más amplios; la regla ya estaba en la Specification). Solicitado por delivery-review (REV-2026-10-09-gastos-reporting-mvp-01).
- **v3** (2026-10-09): [Specification] UI-03 reformulado: ya no prohíbe las palabras "costo", "margen" y "utilidad" sino que exige no afirmarlas ni insinuarlas (pueden aparecer para negarlas, como en la nota fija del dashboard y en el criterio de API-04). Cambio aprobado explícitamente por el usuario; no modifica comportamiento ni código. Solicitado por delivery-review (REV-2026-10-09-gastos-reporting-mvp-02).
