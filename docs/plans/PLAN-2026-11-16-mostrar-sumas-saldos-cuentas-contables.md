# PLAN-2026-11-16-mostrar-sumas-saldos-cuentas-contables (v1)

**Task:** TASK-mostrar-sumas-saldos-cuentas-contables · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-mostrar-sumas-saldos-cuentas-contables-pantalla-saldos / Ninguno

## Objective
Mostrar, para todas las cuentas del plan de la empresa, las sumas de Debe/Haber y los saldos deudor/acreedor calculados sobre el libro de asientos (acumulado o por rango), con filtros y acceso a los movimientos de cada cuenta.

## Context
CONT-04. Las dependencias (asientos CONT-02, cuentas CONT-09, períodos CONT-10) están en la rama `accounting`; el PR apunta a `accounting`. Ver el TASK.

# Specification

## Domain context
Bounded context `accounting`. Solo lectura sobre `JournalEntryModel`/`JournalLineModel` y `AccountModel`; no toca otros módulos.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Total Debe / Total Haber | Suma de los importes de las líneas en ese lado, dentro del alcance | Tarjeta CONT-04 |
| Saldo deudor | `max(Debe − Haber, 0)` | Tarjeta |
| Saldo acreedor | `max(Haber − Debe, 0)` | Tarjeta |
| Saldo inicial | Saldo neto acumulado de las líneas con fecha contable anterior a `date_from`, expresado como deudor/acreedor | Tarjeta |
| Saldo final | Saldo acumulado de todas las líneas con fecha contable ≤ `date_to` (o sin límite) | Tarjeta |
| Fecha contable | `accounting_date` de la cabecera del asiento (también para reversiones) | `journal.py:121` |

## Current behavior
Sin endpoint de saldos por cuenta sobre asientos; `totals_by_account` suma todo sin fechas (`repositories.py` ~560); la pantalla Saldos es «Próximamente» (`balances-page.component.ts`).

## Expected behavior
`GET /api/accounting/balances/` devuelve todas las cuentas de la empresa que cumplan los filtros (activas y deshabilitadas, con o sin movimientos) con sus cifras y unos totales. La UI de Saldos las muestra y enlaza a Movimientos.

## Domain rules / invariants
- **INV-01** (nueva): saldo deudor = max(Debe−Haber, 0), acreedor = max(Haber−Debe, 0), calculado siempre por Debe/Haber de la propia cuenta; nunca por clasificación ni por entradas−salidas.
- **INV-02**: sin `date_from`: Debe/Haber = acumulado hasta `date_to` (o todo) y no hay saldo inicial. Con `date_from`: saldo inicial = neto de líneas con fecha < `date_from`; Debe/Haber = líneas con `date_from ≤ fecha ≤ date_to`; saldo final = neto(inicial) + Debe − Haber del rango, expresado como deudor/acreedor.
- **INV-03**: la inclusión depende solo de `accounting_date` de la cabecera; una reversión cuenta en la fecha de la reversión, no en la del original.
- **INV-04**: solo se suma el libro de asientos; ni `Account.opening_balance` ni el libro de entradas anterior (la apertura son asientos balanceados).
- **INV-05**: aislamiento por `company_id` en toda consulta; un filtro `account_id` de otra empresa → 400.
- **INV-06**: totales = suma de las filas devueltas; con todas las cuentas (sin filtros de cuenta/clasificación), Debe = Haber y deudores = acreedores.

## Acceptance criteria
- **AC-01**: Caja con Debe 1.000 / Haber 300 → deudor 700, acreedor 0; Ingresos con Haber 1.000 → acreedor 1.000, deudor 0.
- **AC-02**: una reversión fechada en diciembre no altera Debe/Haber ni saldos del rango de noviembre y sí el saldo final con fecha ≥ diciembre.
- **AC-03**: una cuenta sin movimientos aparece con todas las cifras en 0,00; una cuenta deshabilitada aparece con su saldo.
- **AC-04**: sin filtros, total Debe = total Haber y total deudor = total acreedor; los filtros (período/rango, clasificación, cuenta) limitan las filas y los totales a lo filtrado y nunca incluyen cuentas de otra empresa.
- **AC-05**: con `date_from`, cada fila trae saldo inicial (deudor/acreedor), Debe/Haber del rango y saldo final acumulado; final = inicial + rango.
- **AC-06**: `period_id` equivale a su `start_date`–`end_date`; combinarlo con `date_from`/`date_to` es 400.
- **AC-07**: cada fila enlaza a Movimientos con `account_id` y el mismo rango (`date_from`/`date_to`); Movimientos pagina como hoy.
- **AC-08**: la UI muestra las columnas del DDR, estados cargando/vacío/error, filtros en la URL, totales y badge «Cuadra/No cuadra».

## Edge cases / Error cases
- `date_from > date_to` → 400 (`date_from`). `period_id`/`account_id` inexistente o de otra empresa → 400. `account_class` inválida → 400.
- Cuenta sin clasificación o código (anteriores): se lista; filtrar por clasificación la excluye.
- Una cuenta con Debe = Haber: ambos saldos 0,00.
- Importes `Decimal` a 2 decimales, serializados como string.

## Authorization / permissions
Autenticado, empresa por `company_id_from(request)`, `required_modules = ('accounting',)`, mismo nivel que la lista de asientos (solo lectura). Sin permisos nuevos.

## API contract
- **API-01** `GET /api/accounting/balances/` con query opcional `period_id`, `date_from`, `date_to`, `account_class`, `account_id`. Respuesta (sin paginar):
  `{ "date_from": "…"|null, "date_to": "…"|null, "has_opening": bool, "rows": [{ "account_id", "code"|null, "name", "account_class"|null, "is_active", "opening_debit_balance", "opening_credit_balance", "debit", "credit", "debit_balance", "credit_balance" }], "totals": { …mismas cifras sumadas… , "balanced": bool } }`.
  `opening_*` valen "0.00" cuando no hay `date_from`. Orden: código (nulos al final), nombre, id. Contrato nuevo, sin compatibilidad hacia atrás que cuidar.

## UI behavior
- **UI-01**: pantalla `balances-page` según el DDR (plantilla Lista de solo lectura con filtros + selector de período), filtros en la URL.
- **UI-02**: enlace por cuenta a `/pocketbiz/accounting/journal?account_id=…&date_from=…&date_to=…` (omite las fechas vacías).
- **UI-03**: columnas de saldo inicial solo con «Desde»; fila de totales y badge «Cuadra/No cuadra».
- **UI-04**: cargando, vacío («Sin registros»), error con «Reintentar», rango inválido.

## Non-functional requirements
Una sola consulta agregada por rango (sin N+1); índice `company_id, account` ya existente. i18n es/en/pt con las mismas claves.

## Out of scope
Cierre de período/asiento de cierre, balance general, estados de resultados, exportación, conversión de divisas, paginación de saldos, cambios al libro de entradas anterior y a `Account.opening_balance`, migraciones.

## Open questions
Ninguna que bloquee. Decisión asumida y registrada: INV-04 (la apertura legada en `Account.opening_balance` no se muestra; se expresa con un asiento de apertura).

# Test Specification

## Unit tests
- Dominio `trial_balance` (puro): saldo deudor/acreedor (AC-01), Debe = Haber → 0/0, composición inicial + rango = final (AC-05), totales y `balanced` (INV-06).

## Integration tests
- Repositorio/servicio y API con BD de test: reversión en otra fecha (AC-02), cuentas sin movimientos y deshabilitadas (AC-03), cobertura completa Debe=Haber y filtros por clasificación/cuenta (AC-04), `period_id` y su exclusión con fechas (AC-06), validaciones 400, aislamiento entre dos empresas (INV-05), módulo `accounting` deshabilitado → 403/rechazo como la lista de asientos.
- Frontend: spec del servicio (query params), spec de la pantalla (columnas, saldo inicial con «Desde», totales, estados, enlace UI-02), prueba de claves i18n (`npm run i18n:check`).

## E2E
**NO** — lectura de un solo paso, cubierta por integración de API y pruebas de componente; sin dependencia nueva.

## Regression tests
Suite existente de `accounting` (backend y frontend) debe seguir verde; `account_balances` y la lista de asientos no cambian.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | Unit dominio + integración API |
| AC-02 | Integración repositorio/API |
| AC-03 | Integración API |
| AC-04 | Integración API (global y filtros, dos empresas) |
| AC-05 | Unit dominio + integración API |
| AC-06 | Integración API |
| AC-07 | Spec de componente (enlaces) |
| AC-08 | Spec de componente + i18n |

# Implementation Plan

## Architecture considerations
Patrón existente: vista → caso de uso → puerto/repositorio. El cálculo (INV-01..03, 06) vive en dominio sin Django; el repositorio solo agrega.

## Proposed solution
1. Dominio `domain/trial_balance.py`: `AccountTotals` (Debe/Haber), `TrialBalanceRow`, `build_row(account, opening, period)`, `build_totals(rows)`, saldo deudor/acreedor.
2. Repositorio: `DjangoJournalRepository.totals_by_account_range(date_from, date_to)` con agregación condicional por fecha en una consulta (suma `Case/When` para inicial y rango).
3. Aplicación `application/trial_balance.py`: `GetTrialBalance(accounts, journal, periods)` resuelve `period_id`, valida filtros, selecciona cuentas y arma filas y totales.
4. API `api/balance_views.py` + serializer de filtros y de salida; ruta `balances/`.
5. Frontend: modelo `models/balances.ts`, `services/balances-api.service.ts`, reescribir `BalancesPageComponent` según DDR, claves `ACCOUNTING.BALANCES.*` en es/en/pt, quitar `SALDOS_PROXIMAMENTE`.

## Files/components affected
- Backend: `domain/trial_balance.py`, `application/trial_balance.py`, `infrastructure/django/repositories.py`, `api/balance_views.py`, `api/balance_serializers.py`, `api/urls.py`, tests `tests/test_trial_balance_domain.py`, `tests/test_trial_balance_api.py`.
- Frontend: `features/accounting/{models,services,pages/balances}`, `assets/i18n/{es,en,pt}.json`.
- Migraciones: ninguna. Docs: este plan, TASK, DDR.

## Implementation steps
1. Dominio + pruebas unitarias (INV-01..03, 06; AC-01, AC-05).
2. Repositorio de agregados por rango + caso de uso (INV-02..05; AC-02, AC-03, AC-06).
3. Vista, serializers y ruta + pruebas de API (AC-04, AC-06, errores, aislamiento, módulo).
4. Modelo y servicio Angular con spec.
5. Pantalla de Saldos, i18n, enlaces y specs (AC-07, AC-08, UI-01..04).
6. `npm run lint`, `npm run i18n:check`, `npm test` y `python manage.py test modules.accounting`.

## Database / migrations
Sin cambios de esquema; solo lectura.

## Risks
- Datos anteriores sin clasificación: se listan como «Sin clasificar».
- Empresas con saldos solo en `opening_balance` legado verán 0 hasta registrar el asiento de apertura (INV-04): se avisa en un texto de apoyo de la pantalla.

## New dependencies
Ninguna.
