# PLAN-2026-11-18-revertir-asiento-al-anular-gasto (v1)

**Task:** TASK-revertir-asiento-al-anular-gasto · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** Ninguno nuevo (reutiliza `DDR-registrar-gastos-cuenta-gasto-pago-formulario-y-detalle` y `ADR-registrar-gastos-cuenta-gasto-pago-puerto-asiento-y-bloqueo`)

## Objective
Anular un gasto contabilizado neutraliza su asiento con **una única** reversión completa (cuentas e importes originales), atribuida a la persona que anula, aunque Contabilidad esté deshabilitada o la configuración haya cambiado; la reversión es visible desde el detalle del gasto. Un gasto sin asiento no genera reversión.

## Context
GAS-01 ya revierte el asiento al anular (`VoidExpense` + `AccountingPosting.reverse`). GAS-02 cierra las brechas respecto a la tarjeta y las prueba. Ver TASK «Hechos encontrados».

# Specification

## Domain context
`expenses` (dueño del gasto) y `accounting` (asientos, períodos). `expenses` depende de `accounting.services`; no al revés.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Asiento original | Asiento `EXPENSE_RECORD` del gasto | GAS-01 |
| Reversión | Asiento de líneas invertidas vinculado al original (`reverses_id`) | `domain/journal.py:183` |
| Anulación | Cambio de estado del gasto a `VOIDED` (lógica, irreversible) | `expense.py:128` |

## Current behavior
Ver TASK. Se revierte el asiento con fecha de hoy y motivo fijo, sin registrar usuario; sin pruebas de los criterios de la tarjeta; el detalle no enlaza la reversión.

## Expected behavior
- Anular un gasto contabilizado: el gasto pasa a `VOIDED` y se crea una reversión con Debe = Haber original de cada línea invertido, mismos importes y cuentas, vinculada al original, con motivo, usuario y fecha; todo en una transacción (si la reversión falla no se anula).
- Anular de nuevo o dos anulaciones simultáneas: una sola reversión (la segunda recibe 409 `expense_already_voided`).
- Anular un gasto sin asiento (anterior al corte, sin cobertura o histórico): solo cambia el estado; no hay reversión.
- La reversión depende de que **exista el asiento original**, no de la cobertura ni de la configuración actuales.

## Domain rules / invariants
- **INV-01** (existente, `reverse_journal_entry`) La reversión invierte todas las líneas del original con sus cuentas y sus importes originales y no consulta configuración vigente.
- **INV-02** Un gasto genera a lo sumo una reversión (idempotencia + bloqueo de fila del gasto).
- **INV-03** Anulación y reversión son atómicas.
- **INV-04** (nuevo) La reversión registra el usuario que anula (`created_by`, `created_by_name`), el motivo `Anulación de gasto` y la fecha de hoy.
- **INV-05** La fecha de la reversión debe caer en un período abierto; un período cerrado nunca se modifica (409 `fiscal_period_closed` / `date_outside_fiscal_period`, el gasto sigue vigente).
- **INV-06** (a confirmar con prueba) Con Contabilidad deshabilitada, un gasto con asiento se anula y se revierte igual.

## Acceptance criteria
- **AC-01** Gasto pagado desde Banco por 200: al anular existe una reversión con Debe Banco 200 / Haber Gasto 200, vinculada al asiento original; los saldos (`journal_balances` / saldos de cuenta) de ambas cuentas quedan neutralizados y el asiento original no cambia.
- **AC-02** Dos anulaciones simultáneas (`TransactionTestCase`) producen una respuesta 200 y una 409, una sola reversión y un gasto `VOIDED`; si la reversión falla (período cerrado) el gasto sigue `ACTIVE` y no queda reversión.
- **AC-03** Tras cambiar la cuenta de la categoría, el mapeo del método de pago y desactivar la cuenta original de gasto y la de pago, anular crea la reversión con las **cuentas originales**.
- **AC-04** Un gasto anterior al corte (Contabilidad habilitada pero sin cobertura para su fecha) no tiene asiento: anularlo no crea reversión ni altera saldos. Con el período del asiento original cerrado y hoy en un período abierto, la reversión se crea en el período abierto y el cerrado no cambia; con hoy en período cerrado, la anulación falla.
- **AC-05** La reversión registra usuario, fecha de hoy y motivo (INV-04).
- **AC-06** Con Contabilidad deshabilitada después de contabilizar el gasto, anularlo crea la reversión (INV-06).
- **AC-07** El detalle del gasto anulado expone `reversal_entry_id` y muestra el enlace «Ver reversión»; el gasto vigente o sin reversión no lo muestra.
- **AC-08** Aislamiento: anular un gasto de otra empresa → 404 y ninguna reversión; las cuentas de otra empresa no intervienen.
- **AC-09** Sin regresiones: reportes de Gastos y listados no cambian.

## Edge cases / Error cases
- **EDGE-01** Gasto marcado contabilizado cuyo asiento no se encuentra: no se inventa reversión (`reverse_automatic_entry` → `None`); se anula solo el estado.
- **EDGE-02** Hoy no cae en ningún período fiscal → 409 `date_outside_fiscal_period`.
- **EDGE-03** Reintento tras anulación exitosa → 409 `expense_already_voided`, sin segunda reversión.

## Authorization / permissions
Permisos existentes de `expenses` (`required_modules = ('expenses',)`). El usuario sale de la sesión autenticada, nunca del cuerpo de la petición. Empresa siempre del usuario autenticado.

## API contract
- **API-01** `POST /api/expenses/<id>/void/` sin cambios de entrada; la respuesta del gasto añade `reversal_entry_id` (UUID | null). Compatible hacia atrás.
- **API-02** `GET /api/expenses/<id>/` (y respuesta de void) añade el mismo campo.
- Errores sin cambios: 409 `{code, detail}`.

## UI behavior
- **UI-01** Detalle del gasto anulado con asiento: junto a «Ver asiento» aparece «Ver reversión» (`/pocketbiz/accounting/journal/<id>`), mismo patrón y estilo (sección «Asiento contable» del DDR de GAS-01). Sin cambios en el botón/diálogo de anulación; el error de período cerrado ya se muestra con la alerta existente.

## Non-functional requirements
Una consulta adicional al detalle (`find_automatic_entry` ya devuelve `reversed_by_id`; sin N+1); `Decimal`; sin migración.

## Out of scope
Campo de motivo libre en la anulación, reversión parcial, reactivar un gasto anulado, retirar la clasificación de egreso, Compras (COM-xx), cambios en `accounting` salvo corrección necesaria según AC-06.

## Open questions (no bloquean)
- ¿La persona quiere capturar un motivo libre al anular? (Se mantiene el motivo fijo; ampliar sería un cambio de contrato aparte.)

# Test Specification

## Unit tests
Caso de uso `VoidExpense` con doble del puerto: recibe y reenvía el actor (INV-04); sigue sin reversar un gasto sin asiento.

## Integration tests
Backend (`expenses/tests/test_voiding_*`, BD y Contabilidad reales): AC-01 (líneas, importes, saldos, vínculo, original intacto), AC-03 (config/cuentas cambiadas), AC-04 (corte; período cerrado/abierto), AC-05 (usuario/fecha/motivo), AC-06 (módulo deshabilitado), AC-07 (campo en API), AC-08 (dos empresas), EDGE-01..03.
Concurrencia: `TransactionTestCase` con `_run_together` (AC-02 y atomicidad ante fallo).
Frontend: spec del detalle (enlace «Ver reversión» solo con `reversalEntryId`), spec del servicio (mapeo del DTO); `i18n:check` y prueba de claves es/en/pt.

## E2E
**NO** — el comportamiento se cubre con pruebas de API contra la fachada real y specs de componentes; no hay flujo multipágina nuevo y evita instalar Playwright.

## Regression tests
Suites completas de `expenses`, `accounting`, `reporting`; `test_boundaries`; specs de `features/expenses`.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | API integración + `journal_balances` |
| AC-02 | `TransactionTestCase` concurrente + API período cerrado |
| AC-03 | API: cambiar categoría/método y desactivar cuentas, luego anular |
| AC-04 | API con gasto anterior al corte y períodos cerrado/abierto |
| AC-05 | API/BD: `created_by`, `accounting_date`, `reversal_reason` |
| AC-06 | API con módulo `accounting` deshabilitado tras contabilizar |
| AC-07 | API (campo) + spec de componente |
| AC-08 | API con dos empresas |
| AC-09 | Suites de regresión |

# Implementation Plan

## Architecture considerations
Seguir el ADR de GAS-01: puerto en `expenses`, adaptador sobre `accounting.services`. Cambio aditivo del puerto: `reverse(expense_id, actor)`.

## Proposed solution
1. Puerto `ExpensePostingGateway.reverse(expense_id, actor_id, actor_name)`; `VoidExpense.execute(expense_id, actor_id=None, actor_name='')` y vista que pasa el usuario autenticado; `AccountingPosting.reverse` reenvía `created_by`/`created_by_name` a `reverse_automatic_entry`.
2. Serializador/vista de detalle: `reversal_entry_id` desde `find_automatic_entry(...).reversed_by_id`.
3. Pruebas AC-01..AC-08 (primero en rojo para AC-06: si falla, corregir en la fachada de `accounting`).
4. Frontend: `reversalEntryId` en modelo y servicio, enlace «Ver reversión» e i18n es/en/pt.

## Files/components affected
- **expenses:** `application/{ports,commands}.py`, `infrastructure/adapters.py`, `api/{views,serializers}.py`, pruebas (`test_posting_application.py`, nuevo `test_voiding_api.py`, nuevo `test_voiding_concurrency.py`).
- **accounting:** solo si AC-06 revela una dependencia de la cobertura/módulo (`services.py`).
- **frontend:** `features/expenses/{models/expense.ts, services/expenses-api.service.ts, pages/expense-detail}` y sus specs, `assets/i18n/{es,en,pt}.json`.
- **docs:** TASK y este PLAN.

## Implementation steps
1. Pruebas de integración backend AC-01, 03, 04, 06, 08 sobre el código actual; anotar cuáles fallan (AC-06 en particular).
2. Pasar el actor (INV-04, AC-05): puerto, caso de uso, adaptador, vista; actualizar dobles de prueba.
3. Corregir lo que revelen las pruebas (si aplica, en `accounting/services.py`).
4. `reversal_entry_id` en API (API-01/02, AC-07) con prueba.
5. Prueba de concurrencia (AC-02) y de atomicidad ante fallo.
6. Frontend: modelo, servicio, enlace, i18n y specs (UI-01).
7. Corridas propias: backend (`expenses`, `accounting`, `reporting`), `makemigrations --check`, frontend `npm test`, `npm run lint`, `npm run i18n:check`.

## Risks / New dependencies
Sin dependencias nuevas. Riesgo: AC-06 puede exigir un ajuste en la fachada de `accounting` (se justifica en `## Implementación` y no se duplican reglas en `expenses`).
