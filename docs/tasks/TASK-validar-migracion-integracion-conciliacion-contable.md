# TASK-validar-migracion-integracion-conciliacion-contable: Validar migración, integración y conciliación de `accounting` antes de main (CONT-13)

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** NO
**Rama:** task/TASK-validar-migracion-integracion-conciliacion-contable (base: `accounting`)
**Pull Request:** _sin abrir todavía_
**Fuente:** https://trello.com/c/cTuM9i9k

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-18 | (nuevo) → INVESTIGATION | Task creado desde la tarjeta CONT-13 | delivery-start |
| 2026-11-18 | INVESTIGATION → PLANNING | Validación acotada, sin decisión arquitectónica nueva; sin pantallas | delivery-start |
| 2026-11-18 | PLANNING → ENGINEERING | Specification READY | delivery-start |

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
- `git rev-list --left-right --count origin/main...origin/accounting` = `0 38`: `main` no tiene nada que `accounting` no tenga; `accounting` (c1afaf1, PR #103) lleva 38 commits más. El PR `accounting → main` es, por tanto, un avance sin divergencia. La rama del task se creó desde `origin/accounting`.
- Cadena de migraciones de `accounting`: `0001`…`0011` (`backend/modules/accounting/migrations/`). Las tablas nuevas del libro son `accounting_fiscal_period` (0009), `accounting_journal_entry`/`accounting_journal_line` (0010) y `accounting_posting_account` (0011); `0006` reemplazó la restricción única de `accounting_entry`. Las migraciones 0007–0011 solo crean/alteran estructura (sin `RunPython`).
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
- Los 38 commits de `accounting` llegan a `main` de una vez y el push despliega: el PR debe listar migraciones y recuperación.

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
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
