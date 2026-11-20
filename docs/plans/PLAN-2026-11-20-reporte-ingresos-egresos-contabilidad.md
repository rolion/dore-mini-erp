# PLAN-2026-11-20-reporte-ingresos-egresos-contabilidad (v1)

**Task:** TASK-reporte-ingresos-egresos-contabilidad · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-reporte-ingresos-egresos-contabilidad-pantalla-reporte-mensual / Ninguno

## Objective
Reporte «Ingresos y egresos» en Contabilidad: por mes de un período fiscal, suma de ingresos, egresos y utilidad, con filtros de período y meses y orden por columna.

## Context
Ver `docs/tasks/TASK-reporte-ingresos-egresos-contabilidad.md`. Solo lectura sobre el libro de asientos; el egreso incluye Gastos y Costos (confirmado por el usuario).

# Specification

## Domain context
Bounded context `accounting`. No toca otros módulos.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Ingreso (mes) | Σ (Haber − Debe) de líneas de cuentas INCOME con fecha contable en el mes | `domain/ledger_report.py` (Resultado) |
| Egreso (mes) | Σ (Debe − Haber) de líneas de cuentas EXPENSE y COST en el mes | usuario 2026-11-20 |
| Utilidad (mes) | Ingreso − Egreso | usuario |
| Período | Período fiscal de la empresa (`FiscalPeriod`) | `domain/fiscal_period.py` |

## Current behavior
No hay reporte mensual; solo el resultado total de un rango (`services.py:512`).

## Expected behavior
- Dado un período, la tabla lista cada mes calendario que intersecta el período (con 0 si no hay movimientos) con Ingreso, Egreso y Utilidad; el pie suma las tres columnas de las filas mostradas.
- Sin parámetros se muestra el período por defecto (INV-02) con todos los meses.
- Se puede elegir otro período y uno o más meses; los totales reflejan solo los meses elegidos.
- Cada cabecera ordena la tabla; el primer clic ordena de mayor a menor.

## Domain rules / invariants
- **INV-01** Se usa `accounting_date` del asiento; reversiones cuentan por su propia fecha. Cuentas sin clasificación o de otra clase no cuentan. Importes en `Decimal`, 2 decimales.
- **INV-02** Período por defecto: el abierto que contiene hoy; si ninguno, el abierto con mayor `end_date`; si no hay abiertos, el de mayor `end_date`; sin períodos, respuesta vacía.
- **INV-03** Solo se cuentan asientos con fecha dentro del período (los meses parciales en los bordes se recortan a `start_date`/`end_date`).
- **INV-04** Aislamiento por `company_id`.

## Acceptance criteria
- **AC-01** Con asientos de ingresos (Haber 1.000) y gastos (Debe 300) y costos (Debe 200) en enero, la fila de enero muestra Ingreso 1.000,00, Egreso 500,00, Utilidad 500,00.
- **AC-02** Una reversión fechada en febrero resta en febrero y no altera enero.
- **AC-03** El pie suma Ingreso, Egreso y Utilidad de las filas mostradas.
- **AC-04** Sin parámetros se usa el período por defecto (INV-02); el selector de período lo muestra elegido.
- **AC-05** Elegir uno o más meses limita filas y totales; sin elegir, se muestran todos los meses del período.
- **AC-06** Cada cabecera (Mes, Ingreso, Egreso, Utilidad) ordena la tabla; primer clic mayor→menor, segundo menor→mayor; el pie no cambia.
- **AC-07** Meses sin movimientos aparecen en 0,00.
- **AC-08** Datos de otra empresa nunca aparecen.

## Edge cases / Error cases
- Sin períodos fiscales → `period: null`, sin filas, estado vacío.
- `period_id` inexistente o de otra empresa → 400.
- `months` con valor mal formado o fuera del período → 400.
- Utilidad negativa → se marca con color y texto.

## Authorization / permissions
`required_modules = ('accounting',)`; empresa desde el usuario autenticado. Sin permisos nuevos.

## API contract
- **API-01** `GET /api/accounting/income-expense/?period_id=<uuid>&months=2026-01,2026-03` (ambos opcionales). Respuesta 200:
  `{"period": {"id","name","date_from","date_to","status"} | null, "months": [{"month":"2026-01","income":"1000.00","expense":"500.00","profit":"500.00"}], "totals": {"income","expense","profit"}}`. Importes como string con 2 decimales. Endpoint nuevo: sin impacto hacia atrás.

## UI behavior
- **UI-01** Plantilla «Lista de solo lectura con filtros» del design-system (DDR): filtros Período y Mes encima de la tabla, filtros en la URL (`period`, `months`).
- **UI-02** Estados: cargando, error con «Reintentar», vacío sin períodos; meses en 0 visibles.
- **UI-03** Cabeceras ordenables con `aria-sort`; utilidad negativa con `text-danger` y «(pérdida)».
- **UI-04** Ruta `/pocketbiz/accounting/income-expense` y entrada de menú «Ingresos y egresos»; textos en es/en/pt.

## Non-functional requirements
Una sola consulta agregada por mes y clase (sin N+1); sin paginación.

## Out of scope
Gráficos, exportar a Excel/PDF, comparar períodos, desglose por cuenta, conversión de moneda.

## Open questions
Ninguna bloqueante.

# Test Specification

## Unit tests / Integration tests
- Dominio: construcción de meses del período (bordes parciales, >12 meses), signo por clase, utilidad, totales, período por defecto (INV-02).
- Integración backend: API con asientos reales (ingreso/gasto/costo, reversión, otra empresa, sin períodos, `months` inválido, módulo deshabilitado).
- Frontend: servicio API (parseo, query), componente (filtros ↔ URL, orden, pie, estados, utilidad negativa), utilidades de filtros/orden.
- i18n: `npm run i18n:check` y prueba de claves es/en/pt.

## E2E
NO — reporte de solo lectura cubierto por pruebas de API y de componente; no es flujo crítico de punta a punta.

## Regression tests
`sidebar-menu.spec.ts` actualizado con la nueva ruta; suites de accounting existentes sin cambios.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01, AC-07 | Integración backend (API) + unit de dominio |
| AC-02 | Integración backend (reversión) |
| AC-03 | Unit de dominio + componente |
| AC-04 | Unit de dominio (INV-02) + componente |
| AC-05 | Integración backend (`months`) + componente |
| AC-06 | Componente (orden y `aria-sort`) |
| AC-08 | Integración backend (dos empresas) |

# Implementation Plan

## Architecture considerations
Seguir `docs/architecture/ddd.md`: dominio puro sin Django, caso de uso con repositorios por puerto, repositorio Django con agregación, vista DRF delgada, serializer de filtros que valida forma.

## Proposed solution
- Dominio `domain/income_expense.py`: `month_buckets(start, end)`, `MonthResult`, `IncomeExpenseTotals`, `default_period(periods, today)`.
- Aplicación `application/income_expense.py`: `GetIncomeExpense(periods, journal)`.
- Repositorio: `DjangoJournalRepository.result_by_month(date_from, date_to)` → Σ debit/credit por (`TruncMonth(entry__accounting_date)`, `account__account_class`) limitado a INCOME/EXPENSE/COST.
- Vista `api/income_expense_views.py` + serializer + ruta `income-expense/`.
- Frontend: `models/income-expense.ts`, `services/income-expense-api.service.ts`, `pages/income-expense/` (componente, template, scss si hace falta), ruta en `app.routes.ts`, entrada en `assets/data/routes.json`, claves i18n (es/en/pt).

## Files/components affected
- Backend: `modules/accounting/{domain,application,infrastructure/django/repositories.py,api/{income_expense_views,income_expense_serializers,urls}.py}`; tests en `modules/accounting/tests/`.
- Frontend: ver arriba; `sidebar-menu.spec.ts`; `assets/i18n/{es,en,pt}.json`.
- Docs: `docs/design/design-system.md` solo si se añade un patrón reutilizable (cabeceras ordenables).

## Implementation steps
1. Dominio y pruebas unitarias (INV-01…04, AC-03, AC-07).
2. Repositorio `result_by_month` + caso de uso (AC-01, AC-02, AC-08).
3. Vista, serializer y ruta; pruebas de API (API-01, AC-04, AC-05, errores).
4. Modelo y servicio frontend con pruebas.
5. Componente: filtros en URL, tabla, pie, orden, estados (AC-04…06, UI-01…03).
6. Ruta, menú, i18n es/en/pt; `npm run i18n:check`, lint, build.

## Database / migrations
Sin migraciones.

## Risks
Cuentas sin clasificación quedan fuera (documentado). Primer uso de `TruncMonth` en el proyecto: verificar con PostgreSQL.

## New dependencies
Ninguna.
