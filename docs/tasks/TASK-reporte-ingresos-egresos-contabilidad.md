# TASK-reporte-ingresos-egresos-contabilidad: Reporte de ingresos y egresos por mes en Contabilidad

**Etapa actual:** PLANNING
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** SI
**Rama:** task/TASK-reporte-ingresos-egresos-contabilidad
**Pull Request:** _sin abrir todavía_

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-20 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-11-20 | INVESTIGATION → DESIGN | NEEDS_PLAN, pantalla nueva | delivery-start |
| 2026-11-20 | DESIGN → PLANNING | DDR escrito; decisión de negocio resuelta con el usuario | delivery-start |

## Investigación

### Requerimiento
Agregar en Contabilidad un reporte de ingresos y egresos: suma de ingresos y de egresos **por mes dentro de un período fiscal** (por defecto el período fiscal actual abierto). Columnas: Mes, Ingreso, Egreso, Utilidad; pie de tabla con la suma de cada columna. Filtros sobre la tabla: **Mes** (por defecto todos; se pueden elegir uno o más) y **Período** (período fiscal; por defecto el actual). Las cabeceras de la tabla se pueden ordenar (de mayor a menor).

**Aclaración del usuario (2026-11-20):** egreso = cuentas de clasificación Gastos **+ Costos**.

### Hechos encontrados
- `backend/modules/accounting/domain/account_class.py:5-12` — seis clasificaciones fijas (ASSET, LIABILITY, EQUITY, INCOME, EXPENSE, COST).
- `backend/modules/accounting/domain/ledger_report.py:1-6` y `services.py:512-517` — el «Resultado» del libro ya se define como Ingresos − Costos − Gastos por clasificación de cuenta, con cuentas correctoras netas. Este reporte sigue la misma definición, desglosada por mes.
- `backend/modules/accounting/infrastructure/django/repositories.py:583-605` — `movements_by_account` suma Debe/Haber por cuenta y fecha contable (`entry__accounting_date`); no existe agrupación por mes. `JournalLineModel` (`models.py:245`) tiene `debit`, `credit`, `company_id`, `account`; `accounting_date` está en la cabecera del asiento.
- `backend/modules/accounting/infrastructure/django/models.py:18` — `AccountModel.account_class` (nulo en cuentas antiguas: no cuentan como ingreso ni egreso).
- `backend/modules/accounting/domain/fiscal_period.py:63-91` — `FiscalPeriod` con `start_date`, `end_date`, estado `OPEN`/`CLOSED`; el listado existe (`api/urls.py:38`, `fiscal-periods/`) y `frontend/.../services/fiscal-periods-api.service.ts` lo consume.
- `backend/modules/accounting/api/balance_views.py:18-31` y `api/urls.py:61-65` — patrón de vista de solo lectura: `required_modules = ('accounting',)`, `company_id_from`, serializer de filtros, caso de uso con repositorios `Django…Repository(company_id)`.
- `frontend/.../pages/cash-flow/cash-flow.component.ts:27-47,154-168` y `pages/balances/balances-page.component.ts` — pantallas de reporte con filtros en la URL (`ActivatedRoute.queryParamMap`), `Subject` + `switchMap`, estados cargando/error/vacío.
- `frontend/panel_admin/src/app/app.routes.ts:148-157` — rutas `accounting/balances` y `accounting/cash-flow` con `data.module = 'accounting'`; menú en `src/assets/data/routes.json:374` (+ claves `MENUITEMS.ACCOUNTING.LIST.*` y prueba `layout/sidebar/sidebar-menu.spec.ts:64`).
- `docs/design/design-system.md:131-134` — plantilla de reportes; la regla «Ganancia estimada, nunca utilidad» es del módulo Reporting (cifras estimadas); aquí la fuente es el libro de asientos y el usuario pidió explícitamente «Utilidad».

### Hipótesis / supuestos no confirmados
- Asientos de reversión cuentan por su propia fecha contable (igual que CONT-04); no hay asiento de cierre de período, así que no hay que excluir nada.
- Mes = mes calendario de `accounting_date`. Si el período abarca más de 12 meses, cada mes lleva año (`yyyy-MM`).
- Período por defecto: el período abierto que contiene la fecha de hoy; si ninguno la contiene, el abierto más reciente; si no hay abiertos, el más reciente. Sin períodos: estado vacío.
- Meses del período sin movimientos se muestran con 0.
- Orden: sin paginación (pocas filas), se ordena en el cliente; alternar ascendente/descendente al pulsar la cabecera, primer clic descendente (mayor a menor).

### Módulos y dependencias relacionadas
Solo `accounting` (dominio, aplicación, repositorio, API) y su frontend. Sin impacto en otros módulos.

### Implementaciones similares existentes
`GetTrialBalance` (`application/trial_balance.py`) para caso de uso + filtros; `BalancesPageComponent` / `CashFlowComponent` para pantalla de reporte.

### Comportamiento actual
No existe reporte mensual de ingresos/egresos; el resultado solo se ofrece como total de un rango en el libro (`get_ledger_report`).

### Restricciones
Dinero en `Decimal`; filtrar por `company_id`; sin texto hardcodeado (es/en/pt); sin migraciones (solo lectura); sin dependencias nuevas.

### Riesgos identificados
- Cuentas sin clasificación (`account_class` nulo) quedan fuera: se documenta.
- Agrupar por mes con zona horaria: `accounting_date` es `DateField`, sin conversión.

### Veredicto de complejidad
**NEEDS_PLAN** — endpoint nuevo de solo lectura y pantalla nueva en un solo módulo, sin decisión arquitectónica nueva.

### Diseño requerido
**SI** — pantalla nueva de reporte con filtros y tabla ordenable.

## Diseño
DDR-reporte-ingresos-egresos-contabilidad-pantalla-reporte-mensual (docs/design/).

## Arquitectura
No aplica según veredicto.

## Plan
docs/plans/PLAN-2026-11-20-reporte-ingresos-egresos-contabilidad.md (v1, COMPLETO).

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
