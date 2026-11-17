# TASK-mostrar-sumas-saldos-cuentas-contables: Mostrar sumas y saldos de todas las cuentas contables (CONT-04)

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** SI
**Rama:** task/TASK-mostrar-sumas-saldos-cuentas-contables
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/85
**Fuente:** https://trello.com/c/mC3XliRv/8-cont-04-mostrar-sumas-y-saldos-de-todas-las-cuentas-contables

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-16 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-11-16 | INVESTIGATION → DESIGN | NEEDS_PLAN, diseño requerido | delivery-start |
| 2026-11-16 | DESIGN → PLANNING | DDR escrito | delivery-start |
| 2026-11-16 | PLANNING → ENGINEERING | Specification READY, PLAN v1 y PR abiertos | delivery-start |
| 2026-11-16 | ENGINEERING → REVIEW | Implementación y pruebas del plan completas | delivery-build |
| 2026-11-16 | REVIEW → PUBLISH | Quality Gate PASS con reservas (REV-01..03 abiertos, no bloqueantes) | delivery-publish |

## Investigación

### Requerimiento
Fuente: tarjeta de Trello CONT-04 (insumo, no Specification aprobada). Resumen fiel:
- **Objetivo:** saldos para todas las clasificaciones, no solo Caja/Banco.
- **Tabla:** Código, Cuenta, Clasificación, Total Debe, Total Haber, Saldo deudor, Saldo acreedor. Saldo deudor = max(Debe−Haber,0); acreedor = max(Haber−Debe,0). No inferir el saldo por clasificación ni usar entradas−salidas.
- Incluir cuentas sin movimientos y deshabilitadas; filtros de período/rango, clasificación y cuenta.
- Rango: saldo inicial anterior al inicio, débitos/créditos del rango y saldo final acumulado; la fecha contable decide la inclusión.
- Suman asientos confirmados y reversiones según sus fechas. La apertura sale de asientos balanceados, sin campo paralelo que duplique saldos.
- Desde una cuenta se accede a sus movimientos respetando filtros y paginación.
- Pruebas de aceptación de la tarjeta: (1) Caja Debe 1.000/Haber 300 → deudor 700; Ingresos Haber 1.000 → acreedor 1.000; (2) una reversión de diciembre no altera las sumas del rango de noviembre y sí el saldo final de diciembre; (3) cuentas sin movimientos en cero, deshabilitadas conservan saldo; (4) total global Debe=Haber y deudores=acreedores con cobertura completa, los filtros no muestran datos ajenos.
- Dependencias CONT-02, CONT-09, CONT-10 (ya integradas, ver abajo). Reglas transversales: API y UI, aislamiento por empresa, permisos existentes, precisión decimal y moneda existentes, sin conversión de divisas.

### Hechos encontrados
- **Base de trabajo:** las dependencias están en la rama `accounting`, no en `main` (PRs #77, #80, #82, #83, #84 con base `accounting`). La rama del task se creó desde `origin/accounting` (`75f29cc`) y su PR debe apuntar a `accounting`.
- `backend/modules/accounting/domain/journal.py:116-145` — `JournalEntry` (cabecera inmutable, líneas con Debe/Haber exclusivos, `reverses_id`); una reversión es otro asiento con su propia `accounting_date` (`journal.py:183-194`).
- `backend/modules/accounting/infrastructure/django/models.py:198-262` — `JournalEntryModel` / `JournalLineModel` (`debit`, `credit`, índice `company_id, account`; `accounting_date` solo en la cabecera).
- `backend/modules/accounting/infrastructure/django/repositories.py:~560` — `DjangoJournalRepository.totals_by_account(account_ids)` suma Debe/Haber por cuenta **sin filtro de fecha**; no existe consulta por rango.
- `backend/modules/accounting/services.py:428-435` — `journal_balances` (Debe/Haber acumulados, solo cuentas con movimientos; su docstring dice que el signo lo resuelven «los saldos», o sea esta tarea).
- `backend/modules/accounting/services.py:271-279` — `account_balances` calcula `opening_balance + net` del **libro de entradas anterior** (Caja/Banco): es lo que esta tarea no debe reutilizar.
- `backend/modules/accounting/domain/account.py:96-111` — `Account` con `code`, `account_class`, `is_active`, `kind`, `opening_balance` legado (código y clasificación aún pueden ser nulos en cuentas anteriores).
- `backend/modules/accounting/domain/account_class.py:12` — seis clasificaciones fijas (ASSET, LIABILITY, EQUITY, INCOME, EXPENSE, COST).
- `backend/modules/accounting/domain/fiscal_period.py:1-60` y `api/urls.py:35-40` — períodos fiscales por empresa con `start_date`/`end_date`; el listado ya existe (`fiscal-periods/`).
- `backend/modules/accounting/api/journal_views.py:67-81` — vista de lista con `required_modules = ('accounting',)`, `company_id_from`, filtros validados con serializer (`api/journal_serializers.py:11-22`: `date_from`, `date_to`, `account_id`, `source`, `origin_kind`) y paginación `JournalPagination`.
- `frontend/panel_admin/src/app/features/accounting/pages/balances/balances-page.component.ts:1-11` y `.html` — pantalla «Saldos» ya enrutada (`app.routes.ts:138-142`, `data.module = 'accounting'`) que hoy solo muestra «Próximamente» (clave `ACCOUNTING.JOURNAL.SALDOS_PROXIMAMENTE`, `es.json:2861`).
- `frontend/.../pages/journal-list/journal-list.component.ts:28-47` — Movimientos acepta `date_from`, `date_to`, `account_id` en la URL (`/pocketbiz/accounting/journal`) y pagina; es el destino del enlace «ver movimientos».
- `frontend/.../services/fiscal-periods-api.service.ts` — servicio existente para el selector de período.
- `docs/design/design-system.md:131-134` y `:159-163` — plantillas de reporte y de lista de solo lectura con filtros.

### Hipótesis / supuestos no confirmados
- Los saldos salen **solo del libro de asientos** (`journal_*`). El libro de entradas anterior y `Account.opening_balance` no se suman: la tarjeta pide que la apertura venga de asientos balanceados y sin campo paralelo, y sumarlos duplicaría saldos. (Decisión registrada en el PLAN; no cambia reglas de negocio documentadas.)
- Una sola moneda operativa (`FLOW_CURRENCY`); no se convierte ni se agrupa por moneda (la tarjeta lo prohíbe).
- Sin paginación de la tabla de saldos: el plan de cuentas de una empresa es acotado; los totales se calculan siempre sobre todas las cuentas filtradas.

### Módulos y dependencias relacionadas
Solo `accounting` (dominio, aplicación, repositorio, API) y su frontend. Sin impacto en otros módulos.

### Implementaciones similares existentes
Lista de asientos (`journal_views.py`, `journal_queries.py`) para el patrón vista → caso de uso → repositorio; `features/accounting/pages/journal-list` para filtros en URL y enlaces.

### Comportamiento actual
Existe la pantalla Saldos en «Próximamente»; no hay endpoint de saldos por cuenta sobre asientos.

### Restricciones
`Decimal` siempre; aislamiento por `company_id`; el dominio no importa Django; textos con `translate` en es/en/pt; permisos existentes del módulo `accounting`; sin migraciones previsibles (solo lectura).

### Riesgos identificados
- Cuentas anteriores sin clasificación/código: deben listarse igualmente («Sin clasificar»).
- Rendimiento de la agregación por rango (mitigado por el índice `company_id, account` y una consulta agregada).
- Doble conteo si se mezclara el libro anterior (evitado por decisión).

### Veredicto de complejidad
**NEEDS_PLAN** — cálculo financiero nuevo y lectura pura sobre estructuras existentes, sin nuevas tablas, módulos ni decisión arquitectónica.

### Diseño requerido
**SI** — transforma una pantalla existente en un reporte con filtros, estados y enlaces.

## Diseño
DDR: `docs/design/DDR-mostrar-sumas-saldos-cuentas-contables-pantalla-saldos.md`.

## Arquitectura
No aplica según veredicto.

## Plan
`docs/plans/PLAN-2026-11-16-mostrar-sumas-saldos-cuentas-contables.md` (v1, COMPLETO, READY).

## Implementación
**Resumen.** `GET /api/accounting/balances/` (`api/balance_views.py`, `api/balance_serializers.py`) → caso de uso `GetTrialBalance` (`application/trial_balance.py`) → dominio puro `domain/trial_balance.py` (saldo deudor/acreedor, fila, totales) y la consulta agregada `DjangoJournalRepository.movements_by_account` (una consulta, saldo inicial anterior a `date_from` y movimientos del rango por `accounting_date`). En Angular: `models/balances.ts`, `services/balances-api.service.ts` y la pantalla `pages/balances` (reemplaza el «Próximamente»), con claves `ACCOUNTING.BALANCES.*` en es/en/pt (se retiró `SALDOS_PROXIMAMENTE`). Sin migraciones.

**Cobertura.** INV-01/06 y AC-01/03/05 → `test_trial_balance_domain.py`; AC-01..06, INV-02..05 y filtros inválidos → `test_trial_balance_api.py` (reversión en otra fecha, sin movimientos, deshabilitada, rango, período, dos empresas); AC-07/08, UI-01..04 → `balances-page.component.spec.ts` y `balances-api.service.spec.ts`.

**Pantalla de referencia.** Lista de solo lectura con filtros (`journal-list`) + selector de período; reutiliza clases de la plantilla (`badge-outline`, `ngxTableHeader`) y las claves `COMMON.*`. No se creó ningún componente compartido.

**Desviaciones respecto al plan/DDR.**
- La tabla es un `table-responsive` de Bootstrap en lugar de `ngx-datatable`: el pie de **Totales** con el badge «Cuadra/No cuadra» y las columnas condicionales son directos en `tfoot`, y no hay paginación. Anotar en `design-system.md` si se vuelve patrón.
- El selector de período solo rellena Desde/Hasta (el servidor admite `period_id`, pero la UI envía fechas; el resultado es el mismo y la URL queda compartible).
- Pruebas ejecutadas en esta sesión como verificación propia (no es el Quality Gate): `python manage.py test modules.accounting` (327, OK), `ng test` de `features/accounting` (188, OK) y `core/i18n` (19, OK), `npm run lint` y `npm run i18n:check` sin hallazgos. Para correrlas se copió `backend/.env` al worktree por indicación expresa del usuario (archivo ignorado por git) y se creó `backend/.venv` con `requirements/dev.txt`.

**Deuda técnica.** Ninguna nueva. No se revisó la pantalla en navegador (queda para `delivery-publish`).

## Review
**Quality Gate (subagente aislado, 2026-11-16): PASS con reservas.** Sin hallazgos Critical/High; backend `modules.accounting` 327 OK; frontend 1546 OK (cobertura global 86,83 % sentencias); `lint`, `i18n:check` y `build` sin errores; `bandit` sin hallazgos; `npm audit` con 2 moderadas fuera del diff (`node_modules`). No realizadas: ruff/flake8/mypy (no instalados). Visual: verificado en móvil (390 px, claro) con datos de prueba; **no verificado** escritorio 1440 px, tema oscuro, ni estados vacío/error en navegador.

Hallazgos abiertos (no bloquean):
- REV-01 (Medium, IMPLEMENTATION): faltan pruebas del selector de período y de filtros→URL.
- REV-02 (Low, IMPLEMENTATION): falta la prueba de módulo deshabilitado / sin autenticar.
- REV-03 (Low, DESIGN): filtros degradados a ~800 px.

## Publicación
PR #85 listo para aprobación humana (base `accounting`; no se mergea sin aprobación). Sin ADR, auth ni migraciones. Limitaciones conocidas: REV-01..03 y la revisión visual parcial.
