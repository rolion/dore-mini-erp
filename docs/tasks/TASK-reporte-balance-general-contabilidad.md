# TASK-reporte-balance-general-contabilidad: Reporte de Balance general en Contabilidad

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** SI
**Rama:** task/TASK-reporte-balance-general-contabilidad
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/133

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-26 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-11-26 | INVESTIGATION → DESIGN | NEEDS_PLAN, pantalla nueva | delivery-start |
| 2026-11-26 | DESIGN → PLANNING | DDR escrito | delivery-start |
| 2026-11-26 | PLANNING → ENGINEERING | Specification READY, PLAN v1 y PR abiertos | delivery-start |
| 2026-11-26 | ENGINEERING → REVIEW | Implementación y pruebas del plan completas (pruebas de API backend sin ejecutar: sin PostgreSQL ni `DATABASE_URL`) | delivery-build |

## Investigación

### Requerimiento
«En el módulo de contabilidad necesitamos agregar un reporte de balance general. El balance se podrá filtrar por fechas, inicio y fin.»

### Hechos encontrados
- `backend/modules/accounting/api/urls.py:65` — `balances/` ya existe, pero es **Sumas y saldos** (balance de comprobación, CONT-04), no un balance general: lista todas las cuentas con Debe/Haber y saldos deudor/acreedor (`application/trial_balance.py`, `domain/trial_balance.py`). La pantalla se llama «Saldos» (`pages/balances/`, clave `ACCOUNTING.JOURNAL.SALDOS`).
- `backend/modules/accounting/domain/account_class.py:5-12` — seis clasificaciones fijas: ASSET, LIABILITY, EQUITY, INCOME, EXPENSE, COST. Activo/Pasivo/Patrimonio son las tres del balance general; las otras tres forman el resultado.
- `backend/modules/accounting/infrastructure/django/repositories.py:584-606` — `DjangoJournalRepository.movements_by_account(date_from, date_to)` ya devuelve por cuenta el acumulado previo a `date_from` (apertura) y los movimientos del rango, hasta `date_to`, filtrado por `company_id`. Sirve tal cual: **no hace falta consulta nueva ni migración**.
- `backend/modules/accounting/domain/ledger_report.py:164-173` y `domain/income_expense.py:1-5` — el «Resultado» ya se define como Ingresos − Costos − Gastos por clasificación de cuenta (cuentas correctoras quedan netas por su propio saldo).
- `backend/modules/accounting/domain/trial_balance.py:12-14` — el saldo sale solo de Debe y Haber; `AccountMovements` ya modela apertura + rango.
- `backend/modules/accounting/api/balance_views.py:18-31` — patrón de vista de solo lectura (`required_modules = ('accounting',)`, `company_id_from`, serializer de filtros, caso de uso con repositorios `Django…Repository(company_id)`).
- `backend/modules/accounting/application/trial_balance.py:62-72` — validación de rango `date_from > date_to` → `AccountValidationError` (400).
- Frontend: `features/accounting/pages/balances/` (filtros Desde/Hasta en la URL, `Subject`+`switchMap`, estados cargando/error/vacío) y `pages/income-expense/` son las referencias de pantalla de reporte; ruta en `app.routes.ts:160` (`data.module = 'accounting'`), menú en `assets/data/routes.json:416-426` (+ claves `MENUITEMS.ACCOUNTING.LIST.*` y `layout/sidebar/sidebar-menu.spec.ts:65`).
- Referencia de diseño: `docs/design/design-system.md:133-137` (reportes) y el DDR de Ingresos y egresos (`docs/design/DDR-reporte-ingresos-egresos-contabilidad-pantalla-reporte-mensual.md`).

### Hipótesis / supuestos no confirmados
Resueltos con la convención contable estándar (no hay documento del proyecto que los fije); el usuario puede corregirlos antes del merge:
- **Fecha de corte = «Hasta»**: los saldos finales son acumulados desde el inicio del libro hasta esa fecha (un balance general es una foto a una fecha). **«Desde»** parte el cambio en *Saldo inicial* (acumulado antes de «Desde») y *Movimiento* del rango; no recorta los saldos finales.
- Para que el balance **cuadre** con un rango, el resultado se muestra dentro del Patrimonio en dos líneas: *Resultados de ejercicios anteriores* (Ingresos − Costos − Gastos acumulados antes de «Desde») y *Resultado del período* (los del rango). Sin «Desde», el primero es 0.
- Signo: Activo se muestra como Debe − Haber; Pasivo y Patrimonio como Haber − Debe. Una cuenta correctora o con saldo contrario sale negativa y resta en el subtotal.
- Se omiten las cuentas sin saldo inicial, movimiento ni saldo final (todo 0). Las cuentas sin clasificación quedan fuera de las secciones; si tienen saldo, el balance lo avisa y no marca «Cuadra».
- Sin fechas = todo el libro (igual que Saldos). No se aplica el corte contable (`since`) del reporte de flujo, igual que Saldos.
- Sin selector de período fiscal ni exportación (no pedidos).

### Módulos y dependencias relacionadas
Solo `accounting` (dominio, aplicación, API) y su frontend. Sin impacto en otros módulos.

### Implementaciones similares existentes
`GetTrialBalance` (caso de uso y filtros), `BalanceListView`, `BalancesPageComponent`, `IncomeExpenseComponent`.

### Comportamiento actual
No existe un balance general; solo sumas y saldos por cuenta y resultado agregado en el libro.

### Restricciones
`Decimal` para dinero; `company_id` en toda consulta; sin texto hardcodeado (es/en/pt); sin migraciones; sin dependencias nuevas; dominio sin Django.

### Riesgos identificados
- Interpretación del rango (ver supuestos): documentada en la pantalla con una nota breve.
- Cuentas antiguas sin `account_class`: quedan fuera y se avisa.

### Veredicto de complejidad
**NEEDS_PLAN** — endpoint de solo lectura y pantalla nueva en un solo módulo, reutilizando una consulta existente; sin decisión arquitectónica nueva.

### Diseño requerido
**SI** — pantalla nueva de reporte con filtros y tablas por sección.

## Diseño
DDR-reporte-balance-general-contabilidad-pantalla-balance (docs/design/).

## Arquitectura
No aplica según veredicto.

## Plan
docs/plans/PLAN-2026-11-26-reporte-balance-general-contabilidad.md (v1, COMPLETO).

## Implementación
- **Backend** (`backend/modules/accounting/`): `domain/balance_sheet.py` (INV-01..INV-06; AC-01, AC-03, AC-04, AC-05), `application/balance_sheet.py` (`GetBalanceSheet`: valida el rango y reutiliza `movements_by_account`; AC-02, AC-03, AC-06), `api/balance_sheet_serializers.py` y `api/balance_sheet_views.py`, ruta `balance-sheet/` (API-01, AC-07; `required_modules = ('accounting',)`, repositorios con `company_id`). Sin migraciones ni consulta nueva.
- **Frontend** (`features/accounting/`): `models/balance-sheet.ts` (importes como texto, sin float), `services/balance-sheet-api.service.ts`, `pages/balance-sheet/` (filtros Desde/Hasta en la URL, tres secciones, filas de resultado en Patrimonio, bloque de ecuación con badge Cuadra/No cuadra y diferencia, aviso de cuentas sin clasificar, estados cargando/error/vacío; UI-01..04, AC-08, AC-09), ruta `accounting/balance-sheet`, entrada de menú, claves `ACCOUNTING.BALANCE_SHEET.*` y `MENUITEMS.ACCOUNTING.LIST.BALANCE_SHEET` en es/en/pt (UI-05, AC-10).
- **UI:** plantilla «Lista de solo lectura con filtros» siguiendo `pages/balances` e `income-expense` (breadcrumb, `.card`, `table-responsive`, SCSS compacto en móvil); reutiliza `MoneyPipe`. Sin componentes compartidos nuevos.
- **Pruebas:** dominio y caso de uso (10, ejecutadas, OK); API (`test_balance_sheet_api.py`, 7 casos: **escritos pero no ejecutados**, el entorno no tiene PostgreSQL ni `DATABASE_URL` y no se lee `.env`); frontend suite completa 1899 OK (modelo, servicio, componente, menú), `ng lint` y `i18n:check` OK, `ng build` OK. `flake8` limpio en lo nuevo; `ruff` no está instalado.
- **Desviaciones del plan:** ninguna de alcance. El contador de títulos de `sidebar-menu.spec.ts` pasó de 50 a 51 por la nueva entrada de menú. Fórmula del resultado simplificada a Σ(Haber − Debe) de INCOME/COST/EXPENSE (equivale a Ingresos − Costos − Gastos).
- **Deuda / pendiente:** correr `DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test modules.accounting.tests.test_balance_sheet_api` con una BD de pruebas; revisión visual en navegador pendiente.

## Review
_Pendiente_

## Publicación
_Pendiente_
