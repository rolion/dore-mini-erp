# TASK-validar-migracion-integracion-conciliacion-contable: Validar migración, integración y conciliación de `accounting` antes de main (CONT-13)

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** NO
**Rama:** task/TASK-validar-migracion-integracion-conciliacion-contable (base: `accounting`)
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/104
**Fuente:** https://trello.com/c/cTuM9i9k

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-18 | (nuevo) → INVESTIGATION | Task creado desde la tarjeta CONT-13 | delivery-start |
| 2026-11-18 | INVESTIGATION → PLANNING | Validación acotada, sin decisión arquitectónica nueva; sin pantallas | delivery-start |
| 2026-11-18 | PLANNING → ENGINEERING | Specification READY | delivery-start |
| 2026-11-18 | ENGINEERING → REVIEW | Implementación y validación completas | delivery-build |
| 2026-11-18 | REVIEW → PUBLISH | Quality Gate PASS (solo hallazgos Low) | delivery-publish |

## Investigación

### Requerimiento
Fuente: tarjeta Trello CONT-13 (insumo, no Specification aprobada). Objetivo: dejar el módulo contable simplificado listo para revisión e integración a `main`. Comportamiento pedido:
- Validar instalación nueva y actualización desde copia de la base local con migraciones aplicadas; ejecutar el plan de CONT-07 con respaldo y conciliación.
- Verificar los cuatro submenús, la configuración por módulo, clasificaciones, cuentas y períodos.
- Conciliar cada asiento (Debe = Haber), saldos por cuenta, orígenes y ausencia de duplicados del modelo anterior; los saldos de apertura también deben cuadrar.
- Verificar aislamiento por empresa, permisos, reintentos/concurrencia y fallos transaccionales.
- Cubrir flujos con Contabilidad habilitada/deshabilitada y operaciones previas al corte sin contabilización retroactiva accidental.
- Actualizar documentación y preparar el PR `accounting → main` con evidencia, migraciones, limitaciones y recuperación. **La tarjeta no autoriza merge ni despliegue automático.**

Aceptación de la tarjeta: (1) flujo integrado: venta a crédito, cobro parcial, servicio cobrado, compra/recepción/pago, gasto y reversión, con totales y pendientes conciliados; (2) migración repetida no duplica registros y conserva datos acordados; (3) período cerrado bloquea registros y una reversión posterior usa un período abierto y conserva el original; (4) los checks relevantes pasan y el PR documenta resultados reales.

Reglas transversales: precisión decimal y moneda existentes (sin conversión de divisas); aislamiento por empresa y permisos existentes; trabajar sobre `accounting` y verificar el código real antes de modificar contratos. Dependencias declaradas: CONT-07/08/09/10/11/12, CONT-02/04/05, VEN-01, SRV-01, INV-01, COM-01/02, GAS-01/02.

Aclaración del usuario: usar la rama `accounting` como base.

### Hechos encontrados
- `git rev-list --left-right --count origin/main...origin/accounting` = `0 38`: sin divergencia; `accounting` (c1afaf1, PR #103) lleva 38 commits más. **Corrección (verificada en build, `git diff --stat origin/main..origin/accounting`):** el diff neto es de 87 archivos (+4985/−79) y **no contiene ninguna migración**: `main` ya incluye `accounting` 0001–0011 (`git ls-tree origin/main backend/modules/accounting/migrations/`). Lo que añade el PR `accounting → main` son el flujo de dinero (`cash_flow*`, `ledger_report`), el reporte contable en `reporting`, la reversión del asiento al anular un gasto, pantallas de frontend (29 archivos) y documentación. La rama del task se creó desde `origin/accounting`.
- Cadena de migraciones de `accounting` (ya en `main`): `0001`…`0011` (`backend/modules/accounting/migrations/`). Las tablas nuevas del libro son `accounting_fiscal_period` (0009), `accounting_journal_entry`/`accounting_journal_line` (0010) y `accounting_posting_account` (0011); `0006` reemplazó la restricción única de `accounting_entry`. Las migraciones 0007–0011 solo crean/alteran estructura (sin `RunPython`).
- Modelo: `JournalEntryModel` (`infrastructure/django/models.py:198`, único por `(company, origin_kind, origin_id)` en `:236`) y `JournalLineModel` (`:245`, único `(entry, position)` en `:263`); `FiscalPeriodModel` (`:170`); `PostingAccountModel` (`:268`); el libro anterior `EntryModel` (`:122`) sigue existiendo.
- Aplicación contable: `application/journal.py`, `fiscal_periods.py`, `posting.py`, `trial_balance.py`, `cash_flow.py`, `ledger_report.py`, `regularize.py`, `transition_diagnosis.py`; API en `accounting/api/` (`journal_views.py`, `posting_views.py`, `balance_views.py`, `cash_flow_views.py`, `views.py`).
- Integraciones fuera de `accounting`: adaptadores/puertos en `sales`, `receivables`, `expenses`, `purchases` y `reporting` (`*/infrastructure/adapters.py`, `purchases/application/ports.py`).
- Pruebas existentes de `accounting` (40 módulos en `backend/modules/accounting/tests/`) cubren por separado: concurrencia (`test_concurrency`, `test_entry_concurrency`, `test_fiscal_period_concurrency`, `test_journal_concurrency`), migraciones puntuales (`test_migration_0004/0006/0010`), períodos, saldos y posting. `test_unified_journey.py:89,136,153` cubre solo el recorrido unificado de cobros de ventas/servicios sobre el libro anterior. **No existe una prueba que recorra de punta a punta venta a crédito + cobro parcial + servicio + compra/recepción/pago + gasto + reversión sobre el libro de partida doble** (Grep de `test_*` en `accounting/tests`).
- CONT-07 dejó el diagnóstico (`diagnose_ledger_transition`) y la guía `docs/deployment/transicion-partida-doble.md`, que contiene el procedimiento de respaldo/ensayo en copia y la conciliación de la base local del 2026-11-16 (32 entradas = 4 448,50 BOB; 21 pagos sin entrada; 3 empresas sin corte). La **Etapa 2** (conversión del libro anterior a asientos) **no está implementada**: no hay comando de conversión (Grep `convert` en `backend/modules/accounting` solo halla el diagnóstico). Decisión del dueño (2026-11-16, TASK-diagnostico-transicion-partida-doble `## Publicación`): todos los datos locales son de prueba y las 3 empresas sin corte quedan bloqueadas.
- `docs/adr/ADR-adaptar-reportes-libro-partida-doble-lectura-contable-en-reporting.md:32`: los movimientos del libro anterior no entran en el reporte contable; lo anterior al corte es histórico.
- `docs/deployment/activar-accounting.md:8,44` sigue diciendo que el módulo «no incluye partida doble, egresos, saldos iniciales ni reversiones»: **documentación desactualizada** respecto del código.
- Entorno de este worktree: sin `backend/.venv` ni `frontend/panel_admin/node_modules`; existen en la copia principal (`E:\dore-mini-erp\backend\.venv`, `E:\dore-mini-erp\frontend\panel_admin\node_modules`) y se pueden usar sin instalar nada. `psql`/`pg_dump` **no están en el PATH** de esta máquina.

### Hipótesis / supuestos no confirmados
- Que `python manage.py test` de todo el backend pasa en `accounting` HEAD (hay deuda de lint previa; no se ha corrido la suite completa en esta tarea).
- Que la base local `doredb` sigue como la describe la conciliación del 2026-11-16 (las migraciones 0007–0011 no estaban aplicadas entonces); su estado actual se mide durante la ejecución.
- Que las herramientas de PostgreSQL (`pg_dump`/`pg_restore`) están disponibles por Docker o en una ruta no incluida en el PATH; si no, el ensayo en copia se haría con lo disponible y se documenta la limitación.
- Que el libro anterior y el de partida doble pueden coexistir sin doble cómputo porque los reportes contables ignoran lo anterior al corte; se verifica con pruebas, no se asume.

### Módulos y dependencias relacionadas
`accounting` (dueño), `sales`, `receivables`, `purchases`, `expenses`, `inventory`, `dentistry/service_catalog` (servicios), `modularity` (habilitación por empresa), `reporting` (solo lectura). Dependencias entre módulos: `sales/tests/test_boundaries.py`.

### Implementaciones similares existentes
`test_unified_journey.py` (recorrido integrado), `test_migration_0010.py` (prueba de migración con `MigrationExecutor`), `docs/deployment/transicion-partida-doble.md` (formato de evidencia y conciliación).

### Comportamiento actual
El libro de partida doble, los períodos, la configuración de asientos por módulo, el posting de ventas, cobros, servicios, inventario, compras, gastos y la reversión existen y tienen pruebas por separado. Falta la validación integrada, la conciliación sobre una base migrada y la documentación de despliegue actualizada.

### Restricciones
`CLAUDE.md`: no editar migraciones aplicadas, `Decimal` para dinero, aislamiento por `company_id`, no tocar `.env`, avisar antes de instalar dependencias, PostgreSQL (no SQLite). Tarjeta: sin conversión de divisas; sin merge ni despliegue automático. Cada push a `main` despliega a producción (`docs/deployment/github-actions.md`), por eso el PR a `main` debe quedar para aprobación humana.

### Riesgos identificados
- Un defecto de conciliación descubierto aquí puede exigir un arreglo en código de producto; se corrige acotado dentro de este task y se documenta (no se oculta ni se baja el criterio).
- La migración de la base local con datos reales de prueba puede no ser reproducible sin respaldo previo: toda ejecución sobre datos reales se hace sobre una **copia restaurada**, nunca sobre `doredb`.
- Sin `pg_dump` accesible, el ensayo de recuperación quedaría incompleto.
- Los 38 commits de `accounting` llegan a `main` de una vez y el push despliega: el PR debe declarar que no hay migraciones nuevas y la recuperación.

### Veredicto de complejidad
**NEEDS_PLAN** — validación, pruebas integradas y documentación sobre código ya decidido; no hay decisión arquitectónica nueva ni cambio de contrato previsto (cualquier cambio de contrato requeriría ADR y nueva versión del plan).

### Diseño requerido
**NO** — sin pantallas nuevas; la verificación de los submenús es una comprobación del existente.

## Diseño
No aplica (sin UI nueva).

## Arquitectura
No aplica según veredicto.

## Plan
`docs/plans/PLAN-2026-11-18-validar-migracion-integracion-conciliacion-contable.md` (v1) · Modo: COMPLETO · Specification readiness: READY.

## Implementación
Prueba integrada `backend/modules/accounting/tests/test_cont13_integration.py` (6 pruebas, PostgreSQL real): un recorrido único de venta con anticipo y entrega, servicio cobrado, compra con recepción y pago, gasto y anulación, con apertura manual, cuyos 11 saldos por cuenta están calculados a mano y concilian (AC-01, AC-04); período cerrado + reversión en período abierto (AC-03); recepción rechazada sin efectos parciales (AC-07); módulo deshabilitado y anterior al corte sin contabilización retroactiva (AC-05); segunda empresa sin fuga ni efecto, 401 sin sesión (AC-06); reintentos sin duplicados (AC-07). Verificación propia ejecutada y registrada en `docs/deployment/validacion-accounting-a-main.md` (AC-02, AC-10): ensayo `pg_dump` → `pg_restore` → `migrate` x2 en copia de `doredb`, y reversión a 0006 y avance a 0011 sobre la copia. Guías `activar-accounting.md` y `transicion-partida-doble.md` actualizadas (AC-09); cuerpo del PR `accounting → main` redactado en el informe, sin abrirlo (AC-11). Con la confirmación del usuario se hizo `npm ci` en el worktree (sin cambios en `package*.json`); se copió `backend/.env` sin leerlo (ignorado por git).

**Desviaciones del plan:** (1) el PLAN decía que `accounting → main` traía migraciones nuevas: no es así (main ya tiene 0001–0011); se corrigió el hecho en la investigación, sin cambio de Specification (AC-02 sigue validando instalación nueva y actualización). (2) AC-08: no se escribió una prueba nueva de los submenús/configuración; se apoya en las pruebas de API existentes y en la suite de frontend (1702) — ver informe. (3) El estado real de `doredb` ya estaba en 0011, así que el «actualizar desde copia» se ensayó además revirtiendo la copia a 0006 y volviendo a avanzar.

**Deuda técnica:** la Etapa 2 de CONT-07 (conversión del libro anterior) sigue sin implementar; hoy `accounting_entry` está vacío en la base local.

## Review
**Resultado: PASS** (Quality Gate en subagente aislado, 2026-11-18). Ejecutado: prueba nueva 6/6; backend completo 2230 OK; `makemigrations --check` sin cambios; `ruff`, `flake8` y `bandit` sin hallazgos; frontend `i18n:check` (0 faltantes), `lint`, `build` (solo avisos), `npm test` 1702 OK; `npm audit`: 2 moderadas transitivas; sin secretos, `.env` y `node_modules` no rastreados; sin código de producto ni migraciones en el diff. No re-ejecutado por el revisor: el ensayo en la copia de `doredb` (evidencia de build, ver informe).
Hallazgos, todos Low y sin REV abierto bloqueante (resueltos en documentación o declarados como limitación): AC-04 sin verificación de «origen existente» (declarado en el informe); AC-06 sin 403 de miembro en la prueba nueva (cubierto por las pruebas de cada API, declarado); cifra de archivos de frontend corregida a 33; nota de `npm audit` añadida; acoplamiento de la prueba a helpers de `receivables.tests` (precedente en `test_unified_journey.py`).

## Publicación
PR #104 (base `accounting`) listo para aprobación humana; no se mergea. El PR `accounting → main` **no se abrió**: su cuerpo propuesto está en `docs/deployment/validacion-accounting-a-main.md`; abrirlo y mergearlo es decisión humana (el push a `main` despliega a producción). Cambio sensible: toca la integración a producción y documenta datos de la transición contable, aunque no hay código de producto ni migraciones nuevas.
