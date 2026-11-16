# PLAN-2026-11-15-incorporar-egresos-reversion-libro (v1)

**Task:** TASK-incorporar-egresos-reversion-libro · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-incorporar-egresos-reversion-libro-lista-y-detalle-entradas · ADR-incorporar-egresos-reversion-libro-direccion-operacion-y-reversion

## Objective
Extender el libro de Contabilidad para registrar egresos (gasto y pago de compra), con reversión vinculada, idempotencia garantizada en base de datos y atomicidad con la operación de origen, sin afectar los ingresos de ventas y servicios.

## Context
Ver TASK. Base `accounting`. GAS-01, COM-01 y CONT-04/05 consumen este contrato.

# Specification

## Domain context
Bounded context: Contabilidad (propietario). Gastos y Compras lo usan solo por `accounting.services`.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Entrada/movimiento | Fila del libro (`accounting_entry`) | TASK |
| Dirección | `INCOME` (entra dinero) / `EXPENSE` (sale) | catalog.py |
| Operación | `RECORD` (original) o `REVERSAL` | ADR |
| Origen | `(origin_kind, origin_id)`: PRODUCT, SERVICE, EXPENSE, PURCHASE_PAYMENT | ADR |
Inconsistencia declarada: la UI y los textos llaman «Entradas» al libro completo; se conserva el nombre.

## Current behavior
Ver TASK («Hechos encontrados»).

## Expected behavior
`record_entry` registra egresos de gasto/pago de compra con cuenta, clasificación de egreso y fecha efectiva; `reverse_entry` crea el movimiento opuesto vinculado; el saldo de cada cuenta refleja ambos; la API de lectura distingue direcciones y reversiones.

## Domain rules / invariants
- INV-01 (nueva): la dirección la deriva el origen (`PRODUCT`/`SERVICE` → INCOME; `EXPENSE`/`PURCHASE_PAYMENT` → EXPENSE).
- INV-02 (nueva): monto positivo con 2 decimales en `Decimal` (existente `_amount`).
- INV-03 (nueva): un egreso exige `classification_id` activa, de la empresa y de dirección `EXPENSE` (validada por la fachada).
- INV-04 (nueva): única `(empresa, origen, operación)`; a lo sumo una reversión por original.
- INV-05 (nueva): la reversión copia monto, moneda, cuenta y clasificación del original, tiene dirección opuesta y `reverses` no nulo; el original no cambia.
- INV-06 (existente): las entradas no se editan ni se borran; sin endpoint de escritura.
- INV-07 (nueva): saldo de cuenta = `opening_balance` + Σ(INCOME) − Σ(EXPENSE), incluyendo reversiones con su dirección.

## Acceptance criteria
- AC-01: un egreso de 100 Bs reduce el saldo de la cuenta exactamente en 100 Bs.
- AC-02: registrar el mismo origen/operación dos veces (reintento secuencial o concurrente) deja una sola fila; con datos distintos lanza `EntryConflict`.
- AC-03: si falla el registro del movimiento, la transacción del llamante revierte la operación de origen (sin escritura parcial); sin transacción abierta lanza `EntryContractError`.
- AC-04: `reverse_entry` una vez restaura el saldo; repetirla devuelve la reversión existente (`created=False`) y no vuelve a modificar el saldo.
- AC-05: una empresa no consulta, registra ni reversa movimientos, cuentas ni clasificaciones de otra.
- AC-06: ingresos de ventas y servicios y la regularización siguen funcionando sin cambios (regresión); filas existentes quedan `INCOME`/`RECORD`.
- AC-07: la API de lectura expone dirección, operación, clasificación y vínculos de reversión, filtra por `direction` y entrega totales por dirección sin romper `amount`/`by_origin`.
- AC-08: la UI de Entradas muestra egresos y reversiones (DDR) con textos en es/en/pt.

## Edge cases / Error cases
- EDGE-01: monto 0, negativo, float o con más de 2 decimales → `EntryValidationError`.
- EDGE-02: cuenta de otra empresa/inexistente → `EntryValidationError`; moneda distinta de la cuenta → `EntryValidationError`.
- EDGE-03: egreso sin clasificación o con clasificación de ingreso/inactiva/ajena → error de validación (sin crear nada).
- EDGE-04: revertir un origen sin entrada original → `EntryNotFound`.
- EDGE-05: revertir sobre cuenta inactiva se permite (restituye).
- EDGE-06: dos reversiones concurrentes → una crea, la otra recibe la existente.

## Authorization / permissions
Sin endpoints de escritura nuevos. La lectura mantiene el permiso y el bloqueo de módulo actuales.

## API contract
- API-01: `GET /api/accounting/entries/` y `/entries/<id>/` añaden `direction`, `operation`, `classification`, `reversal_of`, `reversed_by`; `origin.kind` suma `EXPENSE` y `PURCHASE_PAYMENT`; filtro `direction`.
- API-02: `totals[]` conserva `currency`, `count`, `amount`, `by_origin` (ingresos `RECORD`) y añade `expense` y `by_direction`.
- Compatible hacia atrás: solo campos nuevos.

## UI behavior
UI-01: filtro «Dirección» y orígenes nuevos. UI-02: insignia de reversión y signo en importes. UI-03: totales de ingresos, egresos y neto por moneda. UI-04: detalle con clasificación y enlace a original/reversión. Plantillas lista/detalle de `design-system.md` (DDR).

## Non-functional requirements
Consultas de lista y totales sin N+1; saldos con una agregación por cuenta; índices para `(company_id, account)` ya existentes y uno nuevo para `reverses`.

## Out of scope
Pantalla de saldos (CONT-04); reportes (CONT-05); registrar gastos/pagos desde sus módulos (GAS-01, COM-01); anulación de gastos; impedir saldo negativo; backfill de egresos anteriores; conversión de moneda.

## Open questions
- ¿Debe impedirse un egreso que deje la cuenta en saldo negativo? (no bloquea; por ahora se permite).

# Test Specification

## Unit tests
Dominio `Entry` (dirección derivada, reversión inmutable, validación de monto/origen, `differences`) — AC-01..AC-04, EDGE-01.

## Integration tests
Fachada con base de datos: `record_entry`/`reverse_entry`/`account_balances`, atomicidad con `transaction.atomic` y excepción forzada, idempotencia y concurrencia con hilos (patrón de `test_entry_concurrency.py`), aislamiento por empresa, migración 0006 sobre datos previos (patrón de `test_migration_0004.py`), API de lectura y totales; regresión de `sales/receivables/regularization` (`test_payment_ledger.py`, `test_regularization.py`). Pruebas de frontend con `provideTestTranslations()` y paridad de claves i18n.

## E2E
NO: el flujo de punta a punta (gasto → libro) llega con GAS-01; aquí la integración se cubre en backend y componentes.

## Regression tests
Suite `accounting`, `sales`, `receivables`, `test_boundaries`.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | integración `account_balances` tras `record_entry` EXPENSE 100 |
| AC-02 | integración (reintento) + concurrencia con hilos |
| AC-03 | integración: excepción tras `record_entry` dentro de `atomic` ⇒ sin filas; sin `atomic` ⇒ `EntryContractError` |
| AC-04 | integración: reversión doble ⇒ saldo original, `created=False` |
| AC-05 | integración con dos empresas |
| AC-06 | regresiones existentes + test de migración |
| AC-07 | pruebas de API (campos, filtro, totales) |
| AC-08 | specs de componente y `npm run i18n:check`/paridad |

# Implementation Plan

## Architecture considerations
Ver ADR. Orden de bloqueo: cuenta → (original) → inserción con punto de guardado.

## Proposed solution
Dominio puro (`direction`, `operation`, `reverses_id`, `classification_id`), repositorio con `insert`/`reverse`/`balances`, fachada con `record_entry` extendido, `reverse_entry`, `account_balances`; serializers y filtros; frontend de lectura.

## Files/components affected
- Backend: `accounting/domain/{catalog,entry}.py`, `infrastructure/django/{models,repositories}.py`, `services.py`, `api/{serializers,views}.py`, `application/use_cases.py`, `migrations/0006_*.py`, tests en `accounting/tests/`.
- Frontend: `features/accounting/{models/entry.ts,pages/entry-list,pages/entry-detail,services/entries-api.service.ts,testing/entry-fixtures.ts}`, `assets/i18n/{es,en,pt}.json`.
- Docs: este PLAN, ADR, DDR, TASK.

## Implementation steps
1. Dominio: catálogo `ORIGIN_DIRECTION`/operaciones; `Entry` con dirección derivada, `classification_id`, `reverses_id`, `Entry.reversal_of(...)` (INV-01, 02, 05; AC-01, AC-04).
2. Modelo y migración 0006 con backfill y nueva restricción única; probar con datos previos (INV-04, AC-06).
3. Repositorio: insertar con idempotencia por operación, `get_by_origin`, `balances`, filtros y `totals` por dirección (AC-02, AC-07).
4. Fachada: `record_entry` (validación de clasificación para egresos), `reverse_entry`, `account_balances`, exportaciones (AC-03, AC-04, AC-05, EDGE-03..06).
5. API de lectura: campos, filtro `direction`, totales (API-01/02).
6. Regresión backend completa y `test_boundaries`.
7. Frontend: modelos, servicio, lista y detalle según DDR, i18n es/en/pt y specs (AC-08).
8. Actualizar documentación del contrato en `docs/architecture/ddd.md` si aplica.

## Database / migrations
Nueva `0006` (no se edita ninguna aplicada): `RunPython`/defaults para filas existentes; quita `accounting_entry_origin_uniq` y crea `accounting_entry_origin_op_uniq`; `CheckConstraint` de coherencia de reversión; índice en `reverses`.

## Risks
Reemplazo de restricción única en producción (backup previo y despliegue antes de que GAS/COM escriban egresos); cambio de forma de `totals` (aditivo); concurrencia de reversión.

## New dependencies
Ninguna.
