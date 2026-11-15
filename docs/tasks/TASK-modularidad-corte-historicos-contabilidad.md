# TASK-modularidad-corte-historicos-contabilidad: Modularidad, fecha de corte y tratamiento de históricos de Contabilidad (CONT-06)

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-modularidad-corte-historicos-contabilidad (creada sobre `task/TASK-cuentas-dinero-clasificaciones`, a pedido del usuario)
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/75 (base: task/TASK-cuentas-dinero-clasificaciones)
**Fuente:** https://trello.com/c/Bkogz7vS/2-cont-06-definir-e-implementar-modularidad-fecha-de-corte-y-tratamiento-de-hist%C3%B3ricos

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-15 | (nuevo) → INVESTIGATION | Task creado desde la tarjeta de Trello; rama base = rama actual (CONT-01, PR 74 sin mergear) | delivery-start |
| 2026-11-15 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | NEEDS_ARCHITECTURE (ciclo de vida de módulos, tablas nuevas, dependencias entre módulos, contrato API) | delivery-start |
| 2026-11-15 | PLANNING → ENGINEERING | Specification READY: tres decisiones de negocio respondidas por el usuario (corte, apertura, desactivación); el resto con criterio propio, en el plan | delivery-start |

## Investigación

### Requerimiento
Insumo de la tarjeta CONT-06 (lista «En curso», tablero «PocketBiz — Contabilidad: egresos, gastos y compras»; **no es una Specification aprobada**; sin checklists ni comentarios). Objetivo: activar la integración contable de forma segura y conservar la independencia operativa de Gastos y Compras. Esperado: con Contabilidad deshabilitada, Gastos y pagos de Compras funcionan sin cuenta ni movimientos; con ella habilitada, las operaciones integradas nuevas exigen cuenta activa y configuración válida con errores antes de confirmar; fecha de corte por empresa documentada y sin contabilizar retroactivamente; saldos de apertura y advertencia de cobertura parcial sin doble conteo; reactivación sin movimientos silenciosos; revisar `requires` de Compras y `ALLOWED_DEPENDENCIES` (quitar purchases → expenses si no hay dependencia funcional, sin ciclos); anular un gasto histórico sin movimiento no crea dinero ficticio y desactivar Contabilidad se bloquea si hay egresos contabilizados cuya reversión no pueda garantizarse. Pruebas de la tarjeta: (1) gasto y pago de compra con Contabilidad deshabilitada funcionan sin movimiento; (2) habilitar no altera históricos ni genera egresos masivos; (3) repetir configuración/activación no duplica saldos ni movimientos; (4) API y frontend aplican las mismas reglas de módulos; (5) anular un gasto anterior al corte sin movimiento no modifica Caja/Banco. Dependencia: CONT-01. Las tarjetas CONT-02, CONT-03, GAS-01/02, COM-01, CONT-04 y CONT-05 dependen de esta (CONT-02 y CONT-03 la tienen como dependencia directa).

**Decisiones del usuario (2026-11-15, vía pregunta):** (a) la fecha de corte se fija al habilitar Contabilidad (por defecto hoy) y solo cambia mientras no haya movimientos, luego es inmutable; empresas con Contabilidad ya habilitada: corte = fecha de su primera entrada (o la de habilitación); (b) el saldo de apertura es un monto inicial por cuenta a la fecha de corte, editable solo antes del primer movimiento de la cuenta; (c) deshabilitar se rechaza (409) si hay movimientos de egreso vigentes sin revertir; lo ocurrido durante una desactivación queda sin movimiento y se informa como periodo sin cobertura; reactivar no recontabiliza.

### Hechos encontrados
- `backend/modules/modularity/domain/modules.py:30-34` — `accounting` tiene solo opcionales `sales`/`receivables`; `purchases` declara `requires=('catalog', 'expenses')` (`:34`). Por defecto habilitados: `customers, sales, expenses, reporting` (`:43`).
- No hay dependencia funcional de Compras hacia Gastos: `grep -i expense backend/modules/purchases` fuera de tests no devuelve nada; los tests de pagos solo comprueban que no se crean gastos (`purchases/tests/test_payment_api.py:144-155`). El `requires` es solo declarativo. `reporting` ya lee Gastos por su fachada (`reporting/infrastructure/adapters.py:12`).
- `backend/modules/sales/tests/test_boundaries.py:12-28` — `ALLOWED_DEPENDENCIES`: `purchases: {catalog, inventory}` (sin `expenses`), `expenses: set()`, `accounting: {receivables, sales}` y `receivables`/`sales` → `accounting`: **ya existe un ciclo de módulos** accounting ⇄ sales/receivables (adaptadores de regularización de históricos y fachada de cobros).
- `backend/modules/modularity/application/use_cases.py:46-80` — `EnableModule` (precondiciones por puerto) y `DisableModule`; no hay gancho de «ya habilitado/deshabilitado» ni bloqueos al deshabilitar por datos. `api/views.py:73-90` expone `POST /api/modules/<key>/enable|disable/` con 409 estructurado; `shared/enable_preconditions.py` es el puerto neutro vigente; `shared/module_gate.py` el de módulos habilitados.
- `docs/adr/ADR-crear-cuentas-mapear-metodos-pago-modulo-y-contrato.md` («Ajuste posterior», 2026-11-14): por indicación del usuario habilitar/deshabilitar `accounting` **no exige configuración previa**; la exigencia de cuenta y configuración se aplica al registrar cada operación.
- `backend/modules/sales/infrastructure/adapters.py:39,178-198` — Ventas registra el cobro en el libro solo si `accounting` está habilitada y, sin cuenta destino válida, rechaza con `payment_method_without_account` antes de confirmar: es el patrón «error antes de confirmar» a replicar.
- `backend/modules/accounting/infrastructure/django/models.py` — `EntryModel` solo modela **ingresos** (`amount > 0`, `origin_kind` PRODUCT/SERVICE, único por `(company_id, origin_kind, origin_id)`); **no existen movimientos de egreso**: son CONT-02, GAS-01 y COM-01. `repositories.py:214` `has_entries_for_account`; `:243` `coverage()` (primera y última fecha y registro del libro).
- `backend/modules/expenses/domain/expense.py:91-97` — `Expense.void` anula lógicamente, sin efecto financiero; no existe movimiento que revertir hoy.
- Frontend: módulos habilitados y sus `requires` llegan de la API (`core/models/module.ts`, `core/guard/module.guard.ts`, `features/settings/pages/module-list`); las reglas viven en el backend, el frontend las muestra. Pantalla de referencia: «Configuración con listados en pestañas y diálogo» (`docs/design/design-system.md:141`) y las pestañas de `features/accounting/pages/accounting-settings`. Libro de entradas con bloque `coverage` (`features/accounting/pages/entry-list`).
- Antecedentes: `TASK-crear-cuentas-mapear-metodos-pago`, `TASK-conciliar-regularizar-pagos-historicos`, `TASK-libro-entradas-filtros-totales`, `TASK-cuentas-dinero-clasificaciones` (rama base, PR 74).

### Hipótesis / supuestos no confirmados (resueltos en el plan)
- Los movimientos de egreso aún no existen: esta tarea define y entrega la **base** (corte, apertura, periodos de cobertura, bloqueo al deshabilitar mediante un contrato listo para CONT-02, fachada de decisión «¿se registra movimiento?») y las pruebas de independencia; la exigencia de cuenta por operación de egreso se aplica en GAS-01/COM-01 usando esta fachada.
- Las entradas de ingresos que ya se registran no cambian (no se rechazan ni recontabilizan por fecha anterior al corte); la regla de corte se aplica a las operaciones de egreso futuras.
- «Periodo sin cobertura» = intervalo entre deshabilitar y volver a habilitar Contabilidad (tras el corte).
- Zona horaria de «hoy»: `TIME_ZONE` del proyecto (`config/settings/base.py:78`).

### Módulos y dependencias relacionadas
`accounting` (ajustes de corte, periodos, apertura, fachada), `modularity` (ciclo de vida y catálogo), `shared` (puerto neutro nuevo), `purchases`/`expenses` solo por el catálogo y el límite de dependencias, frontend `features/accounting` y `features/settings`. Sin cambios en `sales`/`receivables`.

### Implementaciones similares existentes
Puerto neutro de precondiciones (`shared/enable_preconditions.py`), `coverage()` del libro, `has_entries_for_account` para bloquear cambios de cuenta.

### Comportamiento actual
Con Contabilidad deshabilitada, Gastos y Compras funcionan (no la usan). No hay corte, apertura ni registro de periodos de desactivación; deshabilitar siempre se permite; Compras exige Gastos al habilitarse.

### Restricciones
`CLAUDE.md`: `Decimal` para dinero, `company_id` del usuario, migraciones nuevas sin editar las aplicadas, i18n es/en/pt, módulos solo por `services.py`.

### Riesgos identificados
- Quitar `requires` de Compras cambia reglas de habilitación para empresas existentes (más permisivo; no rompe datos).
- Ciclo accounting ⇄ sales/receivables preexistente (se documenta, no se amplía).
- Contrato de bloqueo sin datos de egreso hasta CONT-02 (probado con doble de prueba).
- Empresas con Contabilidad ya habilitada: el corte se completa de forma perezosa (primer acceso) con la regla acordada.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — nuevo gancho de ciclo de vida entre `modularity` y `accounting`, tablas y campo nuevos con migración, cambio del catálogo de módulos y de los límites entre módulos, contrato API ampliado.

### Diseño requerido
**SI** — pestaña de corte y cobertura, saldo de apertura en cuentas y advertencias en el libro.

## Diseño
`docs/design/DDR-modularidad-corte-historicos-contabilidad-corte-apertura-cobertura.md`

## Arquitectura
`docs/adr/ADR-modularidad-corte-historicos-contabilidad-ciclo-de-vida-y-corte.md`

## Plan
`docs/plans/PLAN-2026-11-15-modularidad-corte-historicos-contabilidad.md` (v1, COMPLETO) · Specification readiness: READY

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
