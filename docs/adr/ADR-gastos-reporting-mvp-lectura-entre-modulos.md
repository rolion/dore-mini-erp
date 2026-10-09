# ADR-gastos-reporting-mvp-lectura-entre-modulos: Cómo Reporting lee Sales, Expenses y Customers; definición única de "venta válida"

**Estado:** Propuesto
**Task relacionado:** TASK-gastos-reporting-mvp
**Fecha:** 2026-10-09

## Contexto
Reporting solo lee (`ddd.md:666-750`, `CLAUDE.md`) y necesita agregados de Sales (totales, por canal, por producto, por cliente, pendientes) y de Expenses (total y por categoría), más nombres de Customers. Hoy el límite entre módulos es la fachada `modules/<modulo>/services.py` con DTO inmutables, verificada por `modules/sales/tests/test_boundaries.py` (`main`): `test_modules_only_reach_each_other_through_services` y `test_only_sales_consumes_the_facades_and_nobody_imports_sales`. Este último **prohíbe que cualquier otro módulo importe `modules.sales`**, y [ADR-ciclo-pedido-entrega-cobro-integracion-modulos](ADR-ciclo-pedido-entrega-cobro-integracion-modulos.md) difirió a este task "Reporting leerá las tablas/consultas de Sales por su propia capa de lectura". Sales persiste `total`, `paid_total`, `status`, `payment_status`, `sales_channel`, `order_date`, `customer_id` y los ítems con snapshot (`sales/infrastructure/django/models.py`, `main`). Decisiones de negocio confirmadas por el usuario: **ventas = suma de `total` de pedidos no cancelados, por `order_date`**; **los pagos de pedidos cancelados se ignoran en el MVP**; semana lunes–domingo; pendientes independientes del periodo.

## Decisión

**1. Reporting no toca tablas ajenas: cada módulo dueño expone consultas de lectura en su `services.py`.**
- `modules/sales/services.py` (nuevo, solo lectura): `get_sales_totals(date_from, date_to)`, `get_sales_by_channel(...)`, `get_top_products(..., limit)`, `get_top_customers(..., limit)`, `get_pending_delivery(limit)`, `get_pending_collection(limit)`. Devuelve dataclasses congeladas (`SalesTotals{total, orders_count}`, `ChannelSales{channel, orders_count, total}`, `ProductSales{product_id, product_name, units, amount}`, `CustomerSales{customer_id, orders_count, total}`, `PendingOrder{id, customer_id, order_date, expected_delivery_date, status, payment_status, total, balance}` y `PendingOrders{count, balance_total, rows}`). Las consultas ORM (agregaciones `Sum`/`Count` con `values().annotate()`) viven en `sales/infrastructure/django/read_queries.py`, no en el dominio.
- `modules/expenses/services.py` (nuevo, solo lectura): `get_expense_report(date_from, date_to) -> ExpenseReport{total, rows: [CategoryExpense{category_id, name, active, total}]}`. **El `total` se calcula como la suma de las filas de la misma consulta**, de modo que "la suma de categorías coincide con el total" (REQ-REP-004) se cumple por construcción. Solo gastos `ACTIVE` con `expense_date` en el rango; incluye categorías inactivas con monto > 0.
- `modules/customers/services.py` ya expone `get_customer_names(ids)`; Reporting lo usa para el ranking de clientes y las listas de pendientes (nombre vigente).

**2. Definiciones únicas, propiedad de Sales (un solo lugar para que REP-002/006/007/008/009 no diverjan):**
- **Pedido válido** = `status ≠ CANCELLED` **y con al menos un ítem**. Ventas del periodo = Σ `total` de pedidos válidos con `order_date` entre `date_from` y `date_to` inclusive; cantidad de pedidos = su conteo. Los pagos (`paid_total`) **no** intervienen en ventas ni en ganancia; los pagos de pedidos cancelados no se muestran en el MVP (deuda: sin flujo de reembolso, `REFUNDED` no se produce).
- **Pendiente de entrega** = pedido válido con `status` ∈ {`NEW`, `IN_PREPARATION`, `READY`}. **Pendiente de cobro** = pedido válido (no cancelado) con `total − paid_total > 0` (cualquier estado logístico, incluido `DELIVERED`); `balance_total` = Σ de esos saldos. Un pedido `DELIVERED` y `PARTIAL` aparece solo en cobro. Ninguno depende del periodo.
- **Productos más vendidos:** agrupa los ítems de pedidos válidos del periodo por `product_id`; `units` = Σ `quantity`, `amount` = Σ `subtotal` de ítem (**antes de descuento del pedido**, por lo que la suma de productos puede superar las ventas); `product_name` = snapshot del ítem **más reciente** (por `order_date`, desempate `created_at`). Orden: `units` desc, luego `amount` desc, luego `product_name`. Límite 10.
- **Clientes con mayor compra:** pedidos válidos del periodo con `customer_id` no nulo (los pedidos sin cliente se excluyen del ranking y se indica en la UI); `total` = Σ `total`, `orders_count`. Orden: `total` desc, `orders_count` desc, `customer_id`. Límite 10.
- **Ventas por canal:** pedidos válidos agrupados por `sales_channel`, orden por `total` desc.
- **Pendientes (listas):** hasta 10 filas; entrega ordenada por `expected_delivery_date` asc (sin fecha al final) y luego `order_date`; cobro ordenado por `order_date` asc (más antiguos primero, para cobrar lo atrasado).

**3. Reporting** (`modules/reporting/`) **no tiene modelos ni migraciones.** Estructura: `domain/period.py` (rango de fechas y resolución de periodo, regla de negocio pura), `application/` (`ports.py` con `SalesReader`, `ExpensesReader`, `CustomerNames`, `Clock`; `queries.py` con los casos de uso `GetDashboardSummary`, `GetSalesReport`, `GetExpenseReport`, `GetSalesByChannel`, `GetTopProducts`, `GetTopCustomers`, `GetPendingOrders`), `infrastructure/adapters.py` (implementa los puertos **solo** llamando a `modules.sales.services`, `modules.expenses.services`, `modules.customers.services`) y `api/`. Las reglas de composición viven en `application`: `estimated_profit = sales_total − expenses_total` (`Decimal`, puede ser negativo), `average_ticket = sales_total / orders_count` si `orders_count > 0`, si no `None` (sin división por cero). Se registra en `INSTALLED_APPS` (sin modelos) y en `config/urls.py` como `api/reports/`.

**4. Límites verificados por test.** `test_boundaries.py` se reemplaza por una prueba con **mapa explícito de dependencias permitidas**, siempre solo hacia `services`: `sales → {catalog, customers}`, `reporting → {sales, expenses, customers}`, `customers → ∅`, `catalog → ∅`, `expenses → ∅`; nadie importa `modules.reporting`; nadie importa `modules.accounts`. Se actualiza `docs/architecture/ddd.md` (sección 10 y 7/8) con el mapa y con el cambio de `DELETE` a anulación.

**5. Consistencia entre llamadas.** El dashboard compone varias fachadas sin una transacción común; entre una y otra puede entrar una venta. Con un solo negocio y pocos usuarios se acepta; no se abre una transacción de lectura repetible.

## Alternativas consideradas
- **Reporting lee los modelos ORM de Sales/Expenses (lectura directa de tablas):** es lo que sugería el ADR de integración, la más rápida de escribir y la más acoplada: cualquier cambio de columna rompe Reporting en silencio y contradice `ddd.md` y el test de límites. Descartada; este ADR **complementa/revisa** esa frase del ADR previo (los datos se leen por consulta de lectura del dueño, no por tabla).
- **Reporting con su propio SQL crudo sobre ambas tablas:** igual de acoplada al esquema y con la "definición de venta válida" repetida; descartada.
- **Tabla/vista de reporting o modelo de lectura propio (CQRS):** fuera del MVP según `CLAUDE.md` (CQRS completo) y sobredimensionado para el volumen.
- **Eventos de dominio que alimenten Reporting:** event sourcing/eventos fuera del MVP.
- **Reutilizar `ListOrders` de Sales (`OrderFilters`) y sumar en Reporting:** exige traer todas las filas y rompe el límite de importación; las sumas en SQL son más baratas y correctas.
- **Ventas por base caja (`payment_date`) o por entrega:** descartadas por el usuario (ver Contexto); la base devengada coincide con el ticket promedio definido en REQ-REP-009.
- **Definir "pedido válido" sin exigir ítems:** un pedido vacío (permitido mientras se edita) contaría como venta de 0 y distorsionaría ticket promedio y conteo.

## Estrategia de rollback / mitigación
- **Aditivo:** se añade `services.py` a Sales y Expenses (solo funciones nuevas) y `read_queries.py` en Sales; no se modifican endpoints ni tablas de Sales. Rollback = revertir el PR; sin migraciones en Reporting.
- **Único cambio sensible:** reescribir `test_boundaries.py` (relaja la regla "nadie importa Sales" a "solo Reporting, y solo `services`"). Mitigación: el mapa permitido es explícito y cubre ambas direcciones; si la prueba nueva se rompe, falla CI antes de mezclar.
- **Riesgo de divergencia de derivados:** los totales usan `total` persistido por Sales (escrito solo por el agregado, con prueba de coherencia existente). Se añade una prueba de Reporting que crea pedidos por el agregado y compara ventas con la suma esperada.

## Consecuencias
- Queda fácil: cambiar el esquema interno de Sales o Expenses sin tocar Reporting; una sola definición de venta válida y de pendientes; probar Reporting con fakes sin base de datos.
- Queda más difícil: cada nueva métrica requiere una función en la fachada del dueño; las fachadas de Sales deben mantenerse pequeñas y de solo lectura.
- Deuda aceptada: ventas devengadas no equivalen a dinero cobrado (el dashboard muestra "por cobrar" aparte); pagos de pedidos cancelados invisibles; importes de productos antes de descuento; sin consistencia transaccional entre consultas.
