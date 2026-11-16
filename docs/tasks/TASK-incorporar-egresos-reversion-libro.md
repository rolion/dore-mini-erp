# TASK-incorporar-egresos-reversion-libro: Egresos, reversión e idempotencia en el libro de Contabilidad (CONT-02)

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-incorporar-egresos-reversion-libro (base: `accounting`)
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/77
**Fuente:** https://trello.com/c/hRlnoPrC

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-15 | (nuevo) → INVESTIGATION | Task creado desde la tarjeta CONT-02 | delivery-start |
| 2026-11-15 | INVESTIGATION → ARCHITECTURE | Cambio de contrato y de esquema del libro | delivery-start |
| 2026-11-15 | ARCHITECTURE → DESIGN → PLANNING | ADR y DDR escritos | delivery-start |
| 2026-11-15 | PLANNING → ENGINEERING | Specification READY; PR abierto | delivery-start |
| 2026-11-15 | ENGINEERING → REVIEW | Implementación completa | delivery-build |
| 2026-11-15 | REVIEW → PUBLISH | Quality Gate PASS | delivery-publish |

## Investigación

### Requerimiento
Fuente: tarjeta Trello CONT-02 (insumo, no Specification aprobada). Aclaración del usuario: usar la rama `accounting` como base.

Objetivo: extender el contrato de movimientos existente para soportar salidas de dinero de Gastos y pagos de Compras. Comportamiento esperado de la tarjeta:
- Cada movimiento conserva empresa, cuenta, monto positivo, dirección, fecha efectiva, clasificación y referencia inequívoca al origen.
- El origen se identifica por tipo e ID de gasto o de pago de compra; una compra con varios pagos genera varios movimientos.
- Unicidad por empresa/origen/tipo de operación en base de datos y manejo de reintentos concurrentes.
- Operación de origen y movimiento se confirman en una misma transacción; si falla la integración no queda escritura parcial.
- Reversiones vinculadas al original, mismo monto y cuenta, efecto opuesto; no se borra ni sobrescribe el original.
- No se pueden editar directamente los movimientos automáticos.
- Compatibilidad con los ingresos existentes de ventas y servicios (y sus reversiones si ya existen).

Pruebas de aceptación de la tarjeta: (1) un egreso de 100 Bs reduce el saldo exactamente 100 Bs; (2) reintento o ejecución simultánea del mismo origen produce un único movimiento; (3) un error al guardar el movimiento revierte la operación de origen; (4) revertir una vez restaura el saldo, repetir no lo incrementa de nuevo; (5) una petición de otra empresa no consulta, registra ni revierte movimientos ajenos.

Dependencias: CONT-01 (PR #74) y CONT-06 (PR #75), ambas en `accounting`; CONT-03 (PR #76) también está mergeada. Consumidores posteriores: GAS-01, COM-01, CONT-04/05.

### Hechos encontrados
- `backend/modules/accounting/domain/entry.py:59-98` — `Entry` es un dataclass inmutable solo de ingresos: sin dirección, clasificación, operación ni vínculo de reversión; `differences()` compara los campos del reintento.
- `backend/modules/accounting/domain/catalog.py:25-26` — `ORIGIN_KINDS` es solo `PRODUCT` y `SERVICE`; `DIRECTIONS` (`INCOME`/`EXPENSE`) existe para clasificaciones (`catalog.py:21-22`).
- `backend/modules/accounting/infrastructure/django/models.py:89-130` — `EntryModel`: `UniqueConstraint(company_id, origin_kind, origin_id)` (`accounting_entry_origin_uniq`), `amount > 0`, sin `direction`/`classification`. Solo se inserta.
- `backend/modules/accounting/infrastructure/django/repositories.py:233-253` — `insert()` usa un punto de guardado y, ante `IntegrityError`, devuelve la existente (`created=False`); `totals()` (`:290-300`) suma todas las entradas como ingreso, por moneda y origen.
- `backend/modules/accounting/services.py:147-172` — `record_entry` exige transacción abierta (`EntryContractError`), bloquea la cuenta (`get_for_update`), valida moneda y es idempotente por origen (`EntryConflict` si difieren datos). No valida que la cuenta esté activa (lo hace `validate_money_account`, `:62-73`, quien llama).
- `backend/modules/accounting/services.py:76-82,94` — `validate_classification(company, id, direction)` y `describe_classifications` ya existen (CONT-01/CONT-03).
- No existe cálculo de saldo por cuenta: `opening_balance` es un campo (`models.py:19-20`) y solo `grep` de "saldo" aparece en UI de cuentas; CONT-04 lo mostrará.
- `backend/modules/accounting/api/serializers.py:101-103,106-130` — `ORIGIN_MODULES` mapea PRODUCT→sales y SERVICE→receivables; `serialize_entry`/`serialize_totals` asumen ingresos.
- `backend/modules/accounting/infrastructure/adapters.py:49-71` y `backend/modules/receivables/infrastructure/adapters.py:58-72` — adaptadores existentes que llaman a `record_entry` y traducen `EntryValidationError`/`EntryConflict`.
- `backend/modules/sales/tests/test_boundaries.py:13,24-25` — dependencias permitidas: `expenses` y `purchases` ya pueden depender de `accounting`.
- Migraciones: última `0005_coverage_settings_opening_balance`. Frontend: `frontend/panel_admin/src/app/features/accounting/models/entry.ts` (`EntryOrigin = 'PRODUCT' | 'SERVICE'`), `pages/entry-list/entry-list.component.html:53-57,107-120,151-155`.
- `docs/adr/ADR-pagos-ventas-libro-entradas-integracion-e-idempotencia.md` — convención vigente: puerto en el módulo de origen, cuenta resuelta por el servidor, idempotencia y transacción del llamante.

### Hipótesis / supuestos no confirmados
- No se exige impedir saldo negativo al registrar un egreso (la tarjeta no lo pide); se deja como pregunta no bloqueante.
- No hay endpoint público para reversar: la reversión la dispara el módulo de origen (anulación de gasto, GAS-0x) por la fachada.

### Módulos y dependencias relacionadas
`accounting` (dueño). Consumidores futuros: `expenses`, `purchases` (solo vía `accounting.services`). `receivables` y `sales` no cambian de contrato.

### Implementaciones similares existentes
Adaptadores de cobro de ventas y servicios (arriba); regularización (`domain/regularization.py`), que crea entradas históricas con `record_entry` y debe seguir intacta.

### Comportamiento actual
El libro solo registra ingresos, uno por pago de origen, sin reversión ni saldos; los totales y el filtro de origen asumen ingresos.

### Restricciones
`Decimal` para dinero; nunca editar migraciones aplicadas; aislamiento por `company_id`; sin importar infraestructura entre módulos; frontend sin texto hardcodeado (i18n es/en/pt).

### Riesgos identificados
- Reemplazar la restricción única del libro sobre datos existentes (migración con backfill de `direction`/`operation`).
- Cambiar `totals` rompe a quien lo consume (lista de Entradas); se mantiene compatibilidad aditiva.
- Concurrencia de reversiones: dos reversiones simultáneas del mismo original.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — cambia el esquema del libro (migración sobre datos existentes), su contrato público `accounting.services` y la API de Entradas, y es la base de GAS-01/COM-01/CONT-04.

### Diseño requerido
**SI** — la lista y el detalle de Entradas deben distinguir ingresos, egresos y reversiones y sus totales (sin pantallas nuevas).

## Diseño
Ver `docs/design/DDR-incorporar-egresos-reversion-libro-lista-y-detalle-entradas.md`.

## Arquitectura
Ver `docs/adr/ADR-incorporar-egresos-reversion-libro-direccion-operacion-y-reversion.md`.

## Plan
`docs/plans/PLAN-2026-11-15-incorporar-egresos-reversion-libro.md` (v1, COMPLETO). Specification readiness: READY.

## Implementación
Resumen: el libro registra egresos y reversiones con dirección, operación y clasificación; saldo por cuenta; lectura ampliada en API y UI.

- **Dominio** (`accounting/domain/{catalog,entry}.py`): `ORIGIN_DIRECTION`, `Entry.direction/operation/classification_id/reverses_id`, `Entry.reverse()`, `effect` — INV-01, INV-02, INV-03 (exigencia de clasificación), INV-05, EDGE-01.
- **Persistencia**: modelo y migración `0006` (backfill `INCOME`/`RECORD`, unicidad `(empresa, origen, operación)`, `CheckConstraint` de vínculo de reversión, `OneToOne reverses`, `origin_kind` a 20) — INV-04, AC-06.
- **Repositorio/fachada**: `insert` idempotente por operación, `get_by_origin`, `net_by_account`; `record_entry` extendido (valida clasificación de egreso salvo reintento), `reverse_entry`, `account_balances` — AC-01..AC-05, INV-07, EDGE-02..06.
- **API de lectura**: `direction`, `operation`, `classification`, `reversal_of`, `reversed_by`, filtro `direction`, totales `expense` y `by_direction` — AC-07, API-01/02.
- **Frontend**: modelos, filtro de dirección, signo de egresos, insignia de reversión, totales de egresos y neto, detalle con clasificación y enlaces; i18n es/en/pt — AC-08, UI-01..04.
- **Pruebas**: `test_entry_expenses.py`, `test_entry_expenses_api.py`, `test_migration_0006.py`; specs de `entry.ts`, lista y detalle. Corridas propias: backend completo 1747 OK; frontend `accounting` 96 OK; `ng lint` e `i18n:check` OK (no es el Quality Gate).

Desviaciones respecto al plan:
- `reverse_entry` serializa bloqueando la fila de la cuenta (no la del original); ADR actualizado.
- `by_origin` de los totales sigue solo con PRODUCT/SERVICE (ingresos); el resto va en `expense` y `by_direction`.
- No se actualizó `docs/architecture/ddd.md` (paso 8 del plan): no hubo cambio de convención.

Deuda técnica: los enlaces al documento de origen de `EXPENSE`/`PURCHASE_PAYMENT` quedan en `null` hasta GAS-01/COM-01. UI: pantalla de referencia seguida = lista y detalle de Entradas existentes; sin componentes compartidos nuevos.

## Review
**Quality Gate: PASS** (subagente aislado, 2026-11-15). Sin hallazgos Critical/High/Medium; 5 hallazgos Low abiertos y no bloqueantes: REV-2026-11-15-incorporar-egresos-reversion-libro-01..05 (`docs/reviews/`).

Evidencia: backend completo `Ran 1747 tests ... OK`; pruebas nuevas `Ran 22 tests ... OK`; `makemigrations --check`: No changes detected; frontend `TOTAL: 1454 SUCCESS` (cobertura líneas 88,18 %); `npm run lint` sin errores; `i18n:check` 2011 claves, 0 faltantes; `npm run build` OK; bandit sin hallazgos; `npm audit --omit=dev`: 0 vulnerabilidades; sin secretos en el diff. Revisión visual en navegador (móvil/escritorio/tema oscuro): **no verificada**. Migración 0006 inversa: no ejecutada.

## Publicación
PR #77 listo para aprobación humana (no se mergea). Cambio sensible: **base de datos** (migración `0006` sobre el libro) y contrato de `accounting.services`; respaldo: ADR-incorporar-egresos-reversion-libro-direccion-operacion-y-reversion. Hacer backup antes de desplegar (el deploy ya lo hace) y publicar antes de que GAS-01/COM-01 escriban egresos.
