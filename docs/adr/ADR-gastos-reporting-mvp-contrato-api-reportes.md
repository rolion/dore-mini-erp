# ADR-gastos-reporting-mvp-contrato-api-reportes: Contrato HTTP de Reporting y regla de periodos

**Estado:** Propuesto
**Task relacionado:** TASK-gastos-reporting-mvp
**Fecha:** 2026-10-09

## Contexto
El DDR [dashboard y reportes](../design/DDR-gastos-reporting-mvp-dashboard-y-reportes.md) exige: un selector de periodo común (Hoy / Esta semana / Este mes / Rango) que muestra las fechas efectivas; tarjetas e informes que **cargan y fallan de forma independiente**; la etiqueta/criterio de ventas visible; pendientes independientes del periodo; ticket promedio sin división por cero; Ganancia estimada reproducible. `ddd.md:972-977` prevé `GET /api/reports/dashboard` y `/api/reports/expenses`. Decisiones de negocio confirmadas: semana lunes–domingo en curso; ventas devengadas por `order_date` (ver [ADR-gastos-reporting-mvp-lectura-entre-modulos](ADR-gastos-reporting-mvp-lectura-entre-modulos.md)). Todo es lectura con `IsAuthenticated` global; sin cambios de autenticación.

## Decisión

**Rutas** (`config/urls.py`: `api/reports/`), todas `GET`, solo lectura, sin paginación (resultados acotados):

| Ruta | Contenido | REQ |
|---|---|---|
| `/api/reports/dashboard/` | Indicadores del periodo y contadores de pendientes | REP-001, 005, 009 |
| `/api/reports/sales/` | Total de ventas, cantidad de pedidos, ticket promedio | REP-002, 009 |
| `/api/reports/expenses/` | Total de gastos y desglose por categoría | REP-003, 004 |
| `/api/reports/sales-by-channel/` | Ventas por canal | REP-007 |
| `/api/reports/top-products/` | Productos más vendidos | REP-006 |
| `/api/reports/top-customers/` | Clientes con mayor compra | REP-008 |
| `/api/reports/pending/` | Listas de pendientes de entrega y de cobro | REP-010 |

**Parámetros de periodo** (todas menos `pending`): `period` ∈ `day` | `week` | `month` (por omisión `month`) **o** `date_from` y `date_to` (`AAAA-MM-DD`, inclusive). Si se envían fechas deben venir **ambas**; `period` y fechas a la vez → 400 (`period`). `date_from > date_to` → 400 en `date_to`. Valores inválidos → 400 `{parametro: [mensaje]}`. `pending` no recibe periodo.

**Resolución del periodo** (regla de `domain/period.py`, relativa a la fecha local del servidor, `timezone.localdate()` con `TIME_ZONE` vía el puerto `Clock`):
- `day` = hoy; `week` = **lunes a domingo** de la semana en curso; `month` = primer a último día del mes en curso. Un rango explícito se respeta tal cual (sin tope máximo).
- Toda respuesta con periodo incluye `period: {kind: 'day'|'week'|'month'|'range', date_from, date_to}` para que la UI muestre las fechas efectivas.

**Formas de respuesta** (importes como cadena `"1200.00"`; ids como cadena UUID):
- `dashboard`: `{period, sales_total, orders_count, average_ticket|null, expenses_total, estimated_profit, pending_delivery_count, pending_collection_count, pending_collection_balance, sales_criteria}`.
- `sales`: `{period, total, orders_count, average_ticket|null, criteria}`.
- `expenses`: `{period, total, categories: [{category_id, name, active, total}]}` (suma de `categories[].total` = `total`).
- `sales-by-channel`: `{period, channels: [{sales_channel, orders_count, total}]}`.
- `top-products`: `{period, limit: 10, products: [{product_id, product_name, units, amount}]}`.
- `top-customers`: `{period, limit: 10, customers: [{customer_id, name, orders_count, total}]}`.
- `pending`: `{delivery: {count, rows: [{id, order_date, customer: {id, name}|null, expected_delivery_date|null, status, payment_status, total}]}, collection: {count, balance_total, rows: [{id, order_date, customer, total, balance, status, payment_status}]}}` con `rows` limitado a 10.
- `average_ticket` es `null` si `orders_count = 0` (REQ-REP-009: sin error, la UI muestra "—"). `estimated_profit = sales_total − expenses_total`; puede ser negativo.
- `sales_criteria` / `criteria`: **cadena única** definida en una constante de `reporting/application` (p. ej. "Pedidos no cancelados con al menos un producto, por fecha de pedido; no incluye lo cobrado ni el costo de producción") para que Dashboard y Reportes muestren exactamente el mismo texto (REQ-REP-002, 005). El texto exacto lo fija el plan.
- Una consulta sin datos devuelve ceros y listas vacías con 200, nunca 404.

**Errores:** 400 por parámetros; 401 sin sesión (global). Una falla de una fachada se propaga como 500 solo para esa ruta; las rutas son independientes, por lo que la UI puede reintentar una tarjeta sin recargar el resto.

## Alternativas consideradas
- **Un único `GET /api/reports/dashboard` con todo (indicadores, listas, rankings):** menos llamadas, pero una falla o lentitud en un ranking vacía el dashboard y contradice la carga independiente del DDR. Siete rutas pequeñas son más simples de probar y de reintentar.
- **Tantas rutas como tarjeta (también `sales`, `expenses` separadas del `dashboard`):** el dashboard repite totales que `sales` y `expenses` también entregan; se acepta esa duplicación mínima (misma función de aplicación) a cambio de que cada pantalla use la ruta que necesita sin acoplarse a la otra.
- **Que el frontend calcule el periodo (semana/mes):** duplicaría la regla y los husos horarios; el servidor es la única fuente (y muestra las fechas efectivas).
- **Paginar rankings/pendientes:** el límite fijo (10) cubre el uso; "Ver todos" lleva a la lista de Pedidos, que ya filtra y pagina.
- **`criteria` solo en el frontend:** podría desincronizarse con la definición del servidor; viajar en la respuesta lo mantiene en un lugar.
- **Devolver el nombre del cliente desde Sales:** Sales no debe importar Customers desde una consulta de lectura agregada; Reporting resuelve nombres con `customers.services.get_customer_names` (una consulta por lote).

## Estrategia de rollback / mitigación
Aditivo y de solo lectura: ruta nueva `api/reports/` sin consumidores previos; no altera datos ni contratos existentes. Rollback = revertir el PR o quitar el `include`. Sin migraciones. Mitigación de errores de cálculo: pruebas que fijan fórmulas (ganancia, ticket con 0 pedidos, semana lunes–domingo, bordes de mes y de rango inclusivo) y una prueba de coherencia (suma de categorías = total de gastos).

## Consecuencias
- Queda fácil: tarjetas independientes y reintentables; reproducir la ganancia (`sales_total − expenses_total`); un único texto de criterio.
- Queda más difícil: siete rutas que mantener y documentar; los rankings dependen del límite fijo.
- Deuda aceptada: sin filtro por canal/cliente en los reportes, sin comparación entre periodos ni tendencia mensual, sin exportación; el periodo `week` y `day` dependen de la fecha del servidor (zona `TIME_ZONE`).
