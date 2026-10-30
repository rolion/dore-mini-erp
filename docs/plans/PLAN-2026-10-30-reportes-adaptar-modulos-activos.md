# PLAN-2026-10-30-reportes-adaptar-modulos-activos (v1)

**Task:** TASK-reportes-adaptar-modulos-activos · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-reportes-adaptar-modulos-activos-estados-de-fuente · ADR-reportes-adaptar-modulos-activos-fuentes-opcionales

## Objective
Dashboard y Reportes muestran solo indicadores de módulos activos, explican las ausencias («No disponible: módulo deshabilitado») y nunca calculan una ganancia con una fuente faltante.

## Context
Ver TASK. Decisiones del usuario (2026-10-30): Ventas y Gastos son dependencias opcionales de Reportes; Reportes puede estar activo sin ninguna.

# Specification

## Domain context
Bounded context Reporting (solo lectura); lee Sales, Expenses y Customers por fachadas; `modularity` define el catálogo.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Fuente | Módulo del que un indicador toma datos (Ventas, Gastos, Clientes) | Trello PB-REP-001 |
| No disponible | Fuente deshabilitada; no es cero | Trello |
| Sin registros | Fuente activa sin datos en indicadores de lista/promedio | Trello |
| Ganancia estimada | Ventas − gastos registrados; sin costo de producción ni de ventas | Trello, `queries.py:157` |

## Current behavior
Reportes requiere Ventas y Gastos (`modules.py:21-22`); dashboard y reportes siempre leen ambas (`queries.py:164-181`); solo Clientes se oculta (`reports.component.ts:46-49`).

## Expected behavior
Las tarjetas se adaptan a las fuentes activas según DDR; la API informa las fuentes del dashboard; el catálogo permite apagar Ventas/Gastos con Reportes activo.

## Domain rules / invariants
- INV-01 (existente): ventas = pedidos no cancelados por fecha de pedido; ganancia = ventas − gastos vigentes.
- INV-02 (nueva): sin Ventas o sin Gastos, `estimated_profit` no se calcula (`null`), jamás 0.
- INV-03 (nueva): una fuente deshabilitada no se consulta ni se sustituye por cero.
- INV-04 (existente): Compras, sus pagos y entradas de stock no son gasto ni entran a la ganancia.

## Acceptance criteria
- AC-01: Con Ventas y Gastos activos, los valores de dashboard y reportes y la ganancia (ventas − gastos) son los de hoy.
- AC-02: Con Ventas off, el dashboard marca «No disponible: módulo deshabilitado» en Ventas, Pedidos/ticket, Pendientes de entrega y de cobro y Ganancia; Gastos se sigue mostrando.
- AC-03: Con Gastos off, marca Gastos y Ganancia como no disponibles; Ventas, Pedidos y Pendientes se muestran.
- AC-04: Con ambas off, el dashboard y Reportes cargan sin error y todas las tarjetas dicen «No disponible: módulo deshabilitado».
- AC-05: Fuente activa sin datos: totales y conteos en 0; listas, desgloses, rankings y ticket promedio «Sin registros».
- AC-06: La Ganancia muestra la nota «Ventas menos gastos registrados; no incluye costo de producción ni costo de ventas»; si falta una fuente indica «No disponible…» y qué requiere.
- AC-07: Cada indicador muestra etiqueta, periodo (o «Estado actual») y unidad (Bs / pedidos).
- AC-08: Cambiar el periodo conserva las definiciones MVP y, con fuentes apagadas, no genera peticiones a ellas ni errores/tarjetas rotas.
- AC-09: En Reportes, ventas/canal/productos dependen de Ventas, gastos/categorías de Gastos, clientes de Clientes y Ventas.
- AC-10: Las compras, pagos y entradas de stock no cambian Gastos ni la ganancia (regresión).
- AC-11: Catálogo: Reportes no requiere Ventas ni Gastos (opcionales); se puede habilitar Reportes sin ellas y deshabilitarlas con Reportes activo; Compras sigue requiriendo Gastos.
- AC-12: API: dashboard 200 con `sources` y nulos según fuentes; `sales`, `sales-by-channel`, `top-products`, `pending` → 403 `module_disabled` (module=`sales`) con Ventas off; `expenses` → 403 (module=`expenses`) con Gastos off; sin 500; el cambio rige desde la petición siguiente.
- AC-13: El aislamiento por empresa se mantiene: las fuentes consideradas son las de la empresa del usuario.

## Edge cases / Error cases
- EDGE-01: Ventas on sin pedidos en el periodo: ventas 0.00, pedidos 0, ticket «Sin registros», ganancia = 0 − gastos.
- EDGE-02: Ganancia negativa con ambas fuentes sigue en rojo (comportamiento actual).
- EDGE-03: Fuente apagada con datos históricos: se ignoran (no se leen).
- EDGE-04: Fallo de carga de la lista de módulos: `isDisabled` no asume; el dashboard se guía por `sources` de la API.

## Authorization / permissions
Sin cambios: administrador de la empresa; el permiso por módulo rige (ver API-02).

## API contract
- API-01: `GET /api/reports/dashboard/` añade `sources: {sales: bool, expenses: bool}`; `sales_total`, `orders_count`, `average_ticket`, `pending_delivery_count`, `pending_collection_count`, `pending_collection_balance`, `sales_criteria` = `null` con Ventas off; `expenses_total` = `null` con Gastos off; `estimated_profit` = `null` si falta cualquiera. Con ambas on, idéntico al actual (compatible).
- API-02: `required_modules` — `sales`, `sales-by-channel`, `top-products`, `pending`: `('reporting','sales')`; `expenses`: `('reporting','expenses')`; `top-customers`: `('reporting','sales','customers')`; dashboard: `('reporting',)`.
- API-03: `GET /api/modules/` devuelve Reportes con `requires: []` y `optional: [sales, expenses, customers]`.

## UI behavior
- UI-01: Dashboard con estados por tarjeta según DDR (plantilla «Dashboard y reportes», design-system §5).
- UI-02: Reportes con estados por tarjeta; no pide endpoints de fuentes apagadas.
- UI-03: Texto «Sin registros» sustituye a «Sin datos para este periodo.».
- UI-04: Pantalla de módulos sin cambio de código (usa `requires`/`optional` de la API).

## Non-functional requirements
Sin consultas N+1: una consulta de módulos habilitados por petición; sin dependencias nuevas; importes como texto de 2 decimales.

## Out of scope
Inventario, contadores y otros ítems de PB-MOD-003; incluir compras/pagos/stock en reportes; exportar; desactivación segura (PB-MOD-004); cambiar la definición de ventas o ganancia.

## Open questions
- Textos exactos de periodo/unidad por tarjeta (criterio del DDR; ajustable en review).

# Test Specification

## Unit tests
- `modularity/tests/test_domain.py`: reporting `requires == ()`, `optional ⊇ {sales, expenses, customers}` (AC-11).
- `reporting/tests/test_application.py` (fakes): dashboard por combinación de fuentes (4), ganancia `None` si falta una, nunca consulta la fuente apagada (AC-02..04, INV-02/03).

## Integration tests
- `reporting/tests/test_api.py`: dashboard con cada combinación de módulos (API-01); 403 `module_disabled` por endpoint (API-02); ambas on = valores previos (AC-01); aislamiento por empresa (AC-13).
- `modularity/tests/test_api.py`, `test_enforcement.py`, `test_settings_api.py`: deshabilitar Ventas/Gastos con Reportes activo ya no da 409; Compras sigue requiriendo Gastos; ajustar los casos que usaban la dependencia (AC-11, API-03).
- Regresión INV-04: crear/pagar una compra no altera `expenses_total` ni `estimated_profit` (AC-10).
- Frontend (Karma): `dashboard.component.spec.ts`, `reports.component.spec.ts`, `reporting-api.service.spec.ts` (nulos/`sources`), `report-card`.

## E2E
**NO** — los cuatro estados se cubren con pruebas de componente y API; no es un flujo crítico de punta a punta.

## Regression tests
Specs vigentes de reporting actualizados (nota de ganancia, «Sin registros»).

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | API test ambas on; spec dashboard |
| AC-02, AC-03, AC-04 | Unit queries + API test + specs dashboard/reports |
| AC-05 | Specs dashboard/reports; API test sin datos |
| AC-06 | Spec dashboard (nota y estado no disponible) |
| AC-07 | Spec dashboard (etiqueta/periodo/unidad) |
| AC-08 | Spec dashboard/reports: recarga al cambiar periodo sin peticiones a fuentes apagadas |
| AC-09 | Spec reports por combinación |
| AC-10 | Test de regresión en reporting con Compras |
| AC-11 | test_domain, modularity API tests |
| AC-12 | API tests reporting + enforcement |
| AC-13 | API test de dos empresas |

# Implementation Plan

## Architecture considerations
ADR: puerto `SourceAvailability` en Reporting; gate neutro `shared.module_gate`; sin imports entre infraestructuras; dominio sin Django.

## Proposed solution
Backend: catálogo → `reporting` opcional; puerto + adaptador; `GetDashboardSummary` con disponibilidad; serializer anulable + `sources`; `required_modules` por vista. Frontend: modelo/servicio con `null` y `sources`; tarjeta con estado «No disponible»; dashboard y reportes condicionados por fuente; nota de ganancia; periodo/unidad por tarjeta.

## Files/components affected
- Backend: `modularity/domain/modules.py`; `reporting/application/{ports,queries}.py`, `infrastructure/adapters.py`, `api/{views,serializers}.py`; tests listados.
- Frontend: `features/reporting/{models/report.ts,services/reporting-api.service.ts,components/report-card/*,pages/dashboard/*,pages/reports/*,testing/report-fixtures.ts}` y sus specs.
- Docs: `docs/producto/modulos-implementados.md` (§3.6, §3.7, §5), `docs/architecture/ddd.md` (nota de módulos), `docs/design/design-system.md` §5.
- Migraciones: ninguna.

## Implementation steps
1. Catálogo: `reporting` sin `requires`, con `optional` (AC-11, API-03) + tests de dominio/API.
2. Puerto `SourceAvailability` + adaptador sobre `module_gate` (INV-03).
3. `GetDashboardSummary` y `DashboardSummary` anulables; `estimated_profit` solo con ambas (INV-02, AC-02..04) + tests unitarios.
4. Serializer del dashboard con `sources` y nulos (API-01).
5. `required_modules` por vista (API-02, AC-12) + tests API/enforcement + aislamiento (AC-13).
6. Regresión Compras (AC-10).
7. Frontend: modelos y servicio (nulos, `sources`).
8. `report-card` con estado «No disponible»; dashboard (AC-02..08, AC-06 nota); reportes (AC-09, «Sin registros») + specs.
9. Documentación y design-system.

## Database / migrations
Ninguna.

## Risks
- Contrato anulable del dashboard (único consumidor en el mismo PR).
- Specs de módulos que asumían la dependencia.
- Reglas del 403 en `top-customers` (ahora también exige `sales`).

## New dependencies
Ninguna.
