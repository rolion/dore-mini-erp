# PLAN-2026-11-16-motor-central-asientos-partida-doble (v1)

**Task:** TASK-motor-central-asientos-partida-doble · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** Ninguno / ADR-motor-central-asientos-partida-doble-modelo-y-contrato

## Objective
Entregar el motor central de asientos de `accounting`: asiento con cabecera y líneas en partida doble, atómico, idempotente por evento, inmutable y reversible una sola vez, expuesto por la fachada `accounting.services` para que otros módulos y CONT-11 lo consuman, sin doble contabilización con el libro de entradas actual.

## Context
Ver `docs/tasks/TASK-motor-central-asientos-partida-doble.md`. Base: rama `accounting` (incluye CONT-07…10). Fuente: Trello CONT-02.

# Specification

## Domain context
Bounded context `accounting`. Usa cuentas (CONT-08/09) y `lock_open_period` (CONT-10). Sin dependencias nuevas entre módulos.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Asiento | Cabecera + ≥ 2 líneas con Σ Debe = Σ Haber > 0; confirmado e inmutable | Trello CONT-02 |
| Línea | Cuenta + Debe o Haber positivo (nunca ambos) | Trello CONT-02 |
| Fecha contable | Fecha del asiento; debe caer en período abierto | CONT-10 |
| Origen | `MANUAL`, o `AUTOMATIC` con `(origin_kind, origin_id)` = referencia única de evento | Trello CONT-02 |
| Reversión | Asiento nuevo que invierte todas las líneas, vinculado al original, con motivo y fecha explícita | Trello CONT-02 |
| Libro de entradas | Contrato anterior de una cuenta (`record_entry`) | código actual |

## Current behavior
Solo existe el libro de entradas de una cuenta: `backend/modules/accounting/services.py:155` (`record_entry`), `:190` (`reverse_entry`); sin asientos, líneas ni descripción. `NoJournalPeriodUsage` devuelve 0 (`infrastructure/adapters.py:77`).

## Expected behavior
Los módulos (y CONT-11) publican asientos con `post_journal_entry` y los corrigen con `reverse_journal_entry`, ambos dentro de su transacción. El resultado es único por evento aunque se reintente o compita.

## Domain rules / invariants
- INV-01: ≥ 2 líneas con ≥ 2 cuentas distintas.
- INV-02: cada línea tiene Debe **o** Haber, con importe > 0, `Decimal` con ≤ 2 decimales, máx. 12 dígitos; nunca `float`, negativos ni ambos lados.
- INV-03: Σ Debe = Σ Haber y > 0 (exacto, sin tolerancia).
- INV-04: todas las cuentas son de la empresa, activas, con clasificación habilitada y misma moneda (sin conversión). En reversión las cuentas originales valen aunque estén deshabilitadas.
- INV-05: la fecha contable cae en un período abierto de la empresa (`lock_open_period`); también en reversiones, con su propia fecha.
- INV-06: cabecera, líneas y origen se guardan atómicamente (todo o nada).
- INV-07: único `(empresa, origin_kind, origin_id)`; reintento idéntico devuelve el existente; con datos distintos, conflicto; manuales sin origen nunca colisionan.
- INV-08: un asiento confirmado es inmutable (sin editar ni borrar); un automático no se edita.
- INV-09: reversión: invierte todas las líneas, vincula el original (`reverses`), exige motivo (1-200) y fecha, ocurre una sola vez, no se revierte una reversión y no se reclasifica como nuevo ingreso/gasto (sin origen propio).
- INV-10: no hay doble contabilización: un origen presente en el libro de entradas no se contabiliza como asiento (ADR §4).
- INV-11: toda lectura/escritura filtra por `company_id`.

## Acceptance criteria
- AC-01: Debe Caja 200 + Banco 300 / Haber Ingresos 500 confirma; 499 rechaza sin persistir cabecera ni líneas.
- AC-02: se rechazan: una sola cuenta/dos líneas de la misma cuenta, importe negativo o cero, línea con ambos lados o ninguno, `float`, cuenta de otra empresa, cuenta inactiva o con clasificación deshabilitada, monedas mezcladas, descripción vacía y fecha en período cerrado o sin período.
- AC-03: reintento idéntico del mismo evento devuelve el mismo asiento (`created=False`); datos distintos → conflicto; dos llamadas concurrentes crean un solo asiento; dos eventos con `origin_id` distintos y mismas líneas coexisten.
- AC-04: un fallo al insertar una línea revierte cabecera y origen (nada persiste).
- AC-05: revertir invierte Debe/Haber de todas las líneas, neutraliza saldos por cuenta, vincula el original y registra motivo, fecha y usuario; el original no cambia.
- AC-06: revertir dos veces (secuencial o simultánea) devuelve/crea una sola reversión; revertir una reversión se rechaza; motivo vacío se rechaza.
- AC-07: reversión usa cuentas originales aunque estén deshabilitadas; si el período del original está cerrado, se registra en el período abierto de la fecha dada (y se rechaza si esa fecha no cae en uno abierto).
- AC-08: cambiar límites de un período se rechaza (409 `period_has_entries`) si dejaría asientos fuera, con el adaptador real `JournalPeriodUsage`; cierre concurrente con asiento nunca deja un asiento posterior al cierre (AC-08/AC-09 de CONT-10 con asientos reales).
- AC-09: un origen ya presente en el libro de entradas se rechaza (`origin_in_legacy_ledger`); ninguna llamada del motor escribe en `accounting_entry` ni al revés.
- AC-10: aislamiento por empresa: no se lee ni revierte el asiento de otra empresa (`JournalEntryNotFound`).
- AC-11: conciliación en SQL: para todo asiento Σ Debe = Σ Haber; `journal_balances` coincide con las líneas.
- AC-12: fuera de transacción las funciones públicas fallan con `EntryContractError`.

## Edge cases / Error cases
- Línea con importes de 12 dígitos y 3 decimales; `Decimal('0.00')`; `Decimal` con exponente (p. ej. `1E+2`).
- Asiento con tres líneas (Caja/Banco/Ingresos) y con varias líneas de la misma cuenta pero ≥ 2 cuentas distintas en total: permitido; solo una cuenta total: rechazado.
- Fecha exactamente en el límite del período; fecha con `datetime` en lugar de `date`: rechazada.
- Reversión con fecha anterior a la del original: permitida mientras caiga en período abierto (no hay regla en la tarjeta).
- Cuenta del original desactivada o con clasificación deshabilitada después: la reversión procede; un reintento del original ya creado no se revalida.

## Authorization / permissions
Sin endpoints HTTP nuevos. El llamante entrega `created_by`/`created_by_name` desde la sesión; la empresa sale del usuario autenticado (`shared/tenancy.py`), nunca del cliente. Los permisos de la API de movimientos (administración contable existente) se aplican en CONT-11.

## API contract
Fachada (compatible hacia atrás; no cambia `record_entry` ni `reverse_entry`):
- API-01: `post_journal_entry(company_id, JournalEntryInput) -> PostedJournalEntry` (`entry`, `created`).
- API-02: `reverse_journal_entry(company_id, entry_id, reversal_date, reason, created_by=None, created_by_name='') -> PostedJournalEntry`.
- API-03: `get_journal_entry(company_id, entry_id) -> JournalEntryRef` y `journal_balances(company_id, account_ids=None) -> dict[UUID, JournalBalance]` (Debe, Haber).
- API-04: excepciones públicas: `JournalValidationError(errors)`, `JournalConflict(code, fields)`, `JournalEntryNotFound`, `EntryContractError`, `DateOutsideFiscalPeriod`, `FiscalPeriodClosed`.

## UI behavior
No aplica (sin UI; ver CONT-11).

## Non-functional requirements
Dinero `Decimal(12,2)`. Bloqueo de cuentas en orden determinista para evitar interbloqueos. Índices `(company_id, accounting_date)` y `(company_id, account)`. Sin dependencias nuevas.

## Out of scope
- API HTTP, pantalla de movimientos, formulario manual y confirmación de reversión (CONT-11).
- Configuración de automáticos por módulo y migración de llamantes (CONT-12, VEN-01, SRV-01, COM-01/02, INV-01, GAS-01/02).
- Saldos con signo, reportes y flujo (CONT-04/05); conversión de históricos y conciliación final (CONT-13/etapa 2 de CONT-07).
- Retirar `record_entry`/`reverse_entry`.

## Open questions
- Ninguna que bloquee. A confirmar en CONT-11/13: si la fecha de reversión debe ser ≥ a la del original (hoy permitida con cualquier fecha en período abierto).

# Test Specification

## Unit tests
- Dominio `JournalEntry` sin base de datos: INV-01…INV-03, INV-09, importes con `Decimal` (AC-01, AC-02, AC-05, AC-06).
- Reversión pura (`reverse()`): lados invertidos, mismas cuentas, motivo obligatorio.

## Integration tests
- Fachada (`TestCase`): AC-01, AC-02 (cuentas, monedas, períodos), AC-04 (línea que falla con parche del repositorio), AC-05, AC-07, AC-09, AC-10, AC-11, AC-12.
- Concurrencia (`TransactionTestCase` + `_run_together`): AC-03 (mismo evento ×N), AC-06 (dos reversiones), AC-08 (cierre vs. asiento) y creación de períodos solapados con asientos.
- API de períodos con `JournalPeriodUsage` real: AC-08 (409 `period_has_entries`).
- Migración `0010`: aplica/revierte sobre datos existentes (no toca `accounting_entry`).

## E2E
**NO** — sin UI ni flujo de punta a punta nuevo; la integración completa se valida en CONT-11/13.

## Regression tests
Suite completa de `accounting`, `sales`, `receivables`, `purchases`, `expenses` y `modularity`; `makemigrations --check`; `test_boundaries` de módulos.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | Unit dominio + integración fachada (200+300/500 y 499) |
| AC-02 | Unit dominio + integración fachada |
| AC-03 | Integración + concurrencia |
| AC-04 | Integración con fallo inyectado |
| AC-05 | Unit dominio + integración (saldos) |
| AC-06 | Unit + concurrencia |
| AC-07 | Integración con cuentas deshabilitadas y período cerrado |
| AC-08 | API de períodos + concurrencia |
| AC-09 | Integración con libro de entradas |
| AC-10 | Integración dos empresas |
| AC-11 | Integración con SQL de conciliación |
| AC-12 | Integración |

# Implementation Plan

## Architecture considerations
Seguir el ADR: agregado sin Django en `domain/journal.py`; repositorio `DjangoJournalRepository(company_id)`; casos de uso en `application/journal.py` que reciben puertos (cuentas, períodos, repositorio) para probarse con dobles; la fachada compone adaptadores. Mantener el estilo de `record_entry` (transacción obligatoria, punto de guardado en el `INSERT`). Cuidar `__all__` y que otros módulos solo importen `services`.

## Proposed solution
Ver ADR §1-5.

## Files/components affected
- Backend: `accounting/domain/journal.py` (nuevo), `application/journal.py` (nuevo), `infrastructure/django/models.py` (+`JournalEntryModel`, `JournalLineModel`), `infrastructure/django/repositories.py` (+`DjangoJournalRepository`), `infrastructure/adapters.py` (+`JournalPeriodUsage`, retiro de `NoJournalPeriodUsage`), `api/views.py` (cablear `JournalPeriodUsage`), `services.py` (+fachada y `__all__`), `migrations/0010_journal_entry.py`, docstring de `record_entry`.
- Tests: `accounting/tests/test_journal_domain.py`, `test_journal_service.py`, `test_journal_concurrency.py`, `test_journal_period_usage.py`, `test_migration_0010.py`; ajustes a pruebas de períodos que usaban el adaptador anterior.
- Docs: nota en `docs/architecture/ddd.md` (módulo accounting); TASK y PR.
- Frontend: sin cambios.

## Implementation steps
1. Dominio `JournalEntry`/`JournalLine` + errores y pruebas unitarias (INV-01…03, INV-09; AC-01, AC-02, AC-05, AC-06).
2. Modelos y migración `0010` (checks, únicos, índices) + prueba de migración (INV-06, INV-07).
3. Repositorio: `insert` atómico con punto de guardado, `get`, `get_for_update`, `get_by_origin`, `reversal_of`, saldos (INV-07, INV-11).
4. Casos de uso y fachada `post_journal_entry` (cuentas, `lock_open_period`, idempotencia, rechazo `origin_in_legacy_ledger`) (AC-01…04, AC-09, AC-12).
5. `reverse_journal_entry` con bloqueo del original, cuentas originales y fecha explícita (AC-05…07).
6. `journal_balances`/`get_journal_entry`, conciliación y aislamiento (AC-10, AC-11).
7. `JournalPeriodUsage` y cableado en `api/views.py`; pruebas de períodos con asientos reales y de concurrencia (AC-08).
8. Pruebas de concurrencia de evento y reversión (AC-03, AC-06).
9. Nota en `ddd.md`; suite backend completa y `makemigrations --check`.

## Database / migrations
Nueva `0010_journal_entry` (dos tablas, checks, únicos, índices), dependiente de `0009_fiscal_period`. No edita migraciones aplicadas ni toca `accounting_entry`; reversible con `migrate accounting 0009`.

## Risks
- Interbloqueos al bloquear cuentas y período: orden fijo (cuentas por id, luego período).
- Reintentos que compiten con el cierre: el cierre espera o el asiento ve el período cerrado (contrato de `lock_open_period`).
- Dos libros coexistiendo hasta CONT-12/13: mitigado por INV-10 y la nota en `record_entry`.

## New dependencies
Ninguna.
