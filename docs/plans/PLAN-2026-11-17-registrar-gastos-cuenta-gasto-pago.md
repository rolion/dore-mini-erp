# PLAN-2026-11-17-registrar-gastos-cuenta-gasto-pago (v1)

**Task:** TASK-registrar-gastos-cuenta-gasto-pago · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-registrar-gastos-cuenta-gasto-pago-formulario-y-detalle · ADR-registrar-gastos-cuenta-gasto-pago-puerto-asiento-y-bloqueo

## Objective
Un gasto con Contabilidad cubriendo su fecha genera, en la misma transacción, el asiento Debe cuenta de Gasto / Haber Caja-Banco (evento `EXPENSE_RECORD`), con cuentas por defecto de la configuración y elegibles por gasto, idempotente y bloqueado tras contabilizar. Sin Contabilidad, el flujo operativo no cambia.

## Context
Ver TASK. Reemplaza el contrato anterior (clasificación de egreso / cuenta única con dirección) para Gastos; no se retira el dato histórico.

# Specification

## Domain context
Contexto `expenses` (dueño del gasto) y `accounting` (asientos, configuración, períodos). Gastos depende de `accounting.services`; no al revés.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Cuenta de gasto | Cuenta de clase Gastos que se debita | `posting.py` rol `EXPENSE_BY_CATEGORY` |
| Cuenta de pago | Cuenta de Activo (Caja/Banco) que se acredita | rol `MONEY` |
| Categoría (operativa) | Agrupación de reportes de Gastos; no es una clasificación contable | `expenses/domain/category.py` |
| Contabilizado | El gasto tiene `expense_account_id` y asiento `EXPENSE_RECORD` | este plan |
| Cobertura | Contabilidad habilitada y fecha dentro de su cobertura | `accounting.coverage_status` |

## Current behavior
Ver TASK «Hechos encontrados»: sin asiento, clasificación exigida con cobertura, edición libre.

## Expected behavior
- Con cobertura al crear: se resuelven cuentas (override o configuración), se guarda el gasto y se postea el asiento; todo o nada.
- Sin cobertura: se guarda sin cuentas ni asiento ni errores de configuración.
- Contabilizado ⇒ monto, categoría, fecha, método y cuentas inmutables; descripción, proveedor y notas editables.
- Anular un contabilizado revierte el asiento (fecha de hoy) en la misma transacción.

## Domain rules / invariants
- **INV-01** Debe = Haber = `amount` del gasto; sin líneas de importe cero.
- **INV-02** Un gasto genera a lo sumo un asiento `EXPENSE_RECORD` (`origin_id` = id del gasto).
- **INV-03** Cuenta de gasto: clase Gastos, de la empresa, activa, BOB, habilitada. Cuenta de pago: clase Activo, mismas condiciones.
- **INV-04** Un reintento con la misma `idempotency_key` y los mismos datos no crea otro gasto ni asiento; con otros datos → conflicto.
- **INV-05** Un gasto contabilizado no cambia sus campos financieros; la corrección es anular y registrar de nuevo.
- **INV-06** La reversión de la anulación es única (idempotente) y no borra el asiento original.
- **INV-07** Cambiar la configuración de la categoría o el método no altera gastos ya registrados (las cuentas se guardan como instantánea).
- **INV-08** El proveedor es texto libre opcional; no se exige proveedor formal.

## Acceptance criteria
- **AC-01** Alquiler 500 pagado desde Banco → un gasto y asiento Debe Alquiler 500 / Haber Banco 500 vinculado al gasto.
- **AC-02** Cuenta de gasto o de pago inexistente, de otra empresa, inactiva, de clase incorrecta o en otra moneda → 400 por campo (`expense_account_id` / `payment_account_id`); no queda gasto.
- **AC-03** Si Contabilidad falla (configuración faltante, fecha fuera de período, período cerrado) → error accionable y **no se persiste el gasto**.
- **AC-04** Reintento con la misma clave → mismo gasto (200 `replayed`) y un solo asiento; misma clave con otros datos → 409 `idempotency_key_reused`; dos peticiones concurrentes → un gasto.
- **AC-05** Cambiar la cuenta de la categoría o el mapeo del método después no cambia el gasto ni su asiento (INV-07).
- **AC-06** Sin cobertura (módulo deshabilitado, anterior al corte o hueco) el gasto se registra sin exigir cuentas ni clasificación; no hay asiento.
- **AC-07** Sin cuentas por defecto ni elegidas (con cobertura) → 400 `posting_configuration_missing` con los faltantes y a dónde configurarlos.
- **AC-08** Editar monto, categoría, fecha, método o cuentas de un contabilizado → 409 `expense_posted_locked`; editar descripción, proveedor o notas funciona.
- **AC-09** Anular un contabilizado crea la reversión (Debe Caja-Banco / Haber Gasto) y deja el gasto `VOIDED`; anular de nuevo no duplica; período cerrado → 409 y el gasto sigue vigente.
- **AC-10** Anular un gasto sin asiento (histórico o sin cobertura) funciona sin reversión.
- **AC-11** Aislamiento: nunca se leen ni usan cuentas, gastos ni asientos de otra empresa.
- **AC-12** UI: bloque de cuentas con valores por defecto, vista previa Debe/Haber, avisos, campos bloqueados y detalle del asiento (DDR); es/en/pt.
- **AC-13** Reportes de Gastos y listados existentes no cambian (suman `amount` de vigentes).

## Edge cases / Error cases
- **EDGE-01** Método de pago sin cuenta configurada y sin override de pago → `method_unconfigured`.
- **EDGE-02** Categoría sin cuenta y sin override de gasto → `category_unconfigured`.
- **EDGE-03** Cuenta por defecto que luego se desactiva: el gasto nuevo falla con `account_invalid`; los registrados no se tocan.
- **EDGE-04** Cobertura cambia entre `posting-options` y el guardado: manda el servidor al guardar.
- **EDGE-05** Se envían cuentas sin cobertura: se ignoran (no se guardan).
- **EDGE-06** Misma cuenta como gasto y pago: la clase lo impide (Gastos ≠ Activo).

## Authorization / permissions
Permisos existentes del módulo `expenses` (`required_modules`); `posting-options` los mismos. Empresa siempre del usuario autenticado.

## API contract
- **API-01** `POST /api/expenses/`: nuevos campos opcionales `expense_account_id`, `payment_account_id`, `idempotency_key`; 201 al crear, 200 con `replayed: true` en reintento. Compatible hacia atrás.
- **API-02** `GET /api/expenses/posting-options/?expense_date=&category_id=&payment_method=` → `{covered, reason, expense_account|null, payment_account|null, issues[], expense_accounts[], payment_accounts[]}`.
- **API-03** Gasto (lista/detalle): `posted`, `expense_account`, `payment_account` (`{id, code, name}`), y en detalle `journal_entry_id`. Los campos existentes se mantienen; `classification` sigue como histórico.
- **API-04** Errores: 400 por campo / `posting_configuration_missing`; 409 `{code, detail}` para `expense_posted_locked`, `idempotency_key_reused`, `fiscal_period_closed`, `date_outside_fiscal_period`.

## UI behavior
- **UI-01** Formulario: bloque «Contabilidad» solo con cobertura, plantilla Formulario + panel Debe/Haber (DDR).
- **UI-02** Detalle: sección de asiento y bloqueo con nota; edición limitada.
- **UI-03** Anulación: diálogo existente y alerta de período cerrado.

## Non-functional requirements
`Decimal`; transacción atómica gasto+asiento; `select_for_update` ya usado; una consulta por lote para cuentas en listas; sin N+1.

## Out of scope
Pagos parciales o a crédito (CxP), proveedor formal, impuestos, conversión de divisas, retirar la clasificación de egreso, editar asientos, migrar gastos históricos al motor, Compras (COM-01).

## Open questions (no bloquean)
- ¿Retirar la pantalla de clasificación de egreso en una tarea posterior? (se conserva).

# Test Specification

## Unit tests
Dominio `Expense`: `is_posted`, bloqueo en `update` (INV-05); huella de idempotencia.

## Integration tests
Backend (`expenses/tests`, `accounting/tests`): casos de uso con fake del puerto (AC-03..05, 08..10); fachada `post_automatic_entry` con overrides y `posting_options` (INV-03, EDGE-01..03); API completa con Contabilidad real (AC-01, 02, 06, 07, 11); concurrencia con `TransactionTestCase` (AC-04); migración (AC-13).
Frontend: specs del formulario (bloque, defaults, avisos, bloqueo), detalle, servicio API; `i18n:check` y prueba de claves.

## E2E
**NO** — el flujo se cubre con pruebas de API contra la fachada real y specs de componentes; no hay flujo crítico multipágina nuevo y evita instalar Playwright.

## Regression tests
Suite completa de `accounting`, `expenses`, `reporting`, `sales`, `receivables`; límites de módulos (`test_boundaries`).

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | API integración con asiento real |
| AC-02 | Fachada + API (cuenta ajena/inactiva/clase/moneda) |
| AC-03 | Caso de uso + API: período cerrado / fuera de período / config faltante → sin gasto |
| AC-04 | Caso de uso (misma/otra huella) + TransactionTestCase concurrente |
| AC-05 | API: cambiar config tras crear; gasto y asiento intactos |
| AC-06 | API con módulo deshabilitado / antes del corte |
| AC-07 | API 400 con issues |
| AC-08 | Dominio + API 409 y 200 en campos editables |
| AC-09 | API void con reversión, repetido, período cerrado |
| AC-10 | API void sin asiento |
| AC-11 | API con dos empresas |
| AC-12 | Specs de componentes + i18n:check + revisión visual en publish |
| AC-13 | Pruebas existentes de reporting/listado |

# Implementation Plan

## Architecture considerations
Seguir ADR: puerto en `expenses`, adaptador sobre `accounting.services`, extensión aditiva de la fachada. Sin FK entre módulos.

## Proposed solution
Ver ADR (decisiones 1-3).

## Files/components affected
- **accounting:** `services.py` (`account_overrides`, `validate_posting_account`, `posting_options`, exports), `application/posting.py` (overrides en `resolve_event`), pruebas.
- **expenses:** `domain/expense.py`, `domain/exceptions.py`, `application/{commands,ports,queries}.py`, `infrastructure/adapters.py`, `infrastructure/django/{models,mappers,repositories}.py`, `api/{serializers,views,urls}.py`, migración `0004`, pruebas.
- **frontend:** `features/expenses/{models,services,pages/expense-form,pages/expense-detail}`, i18n `es/en/pt`.
- **docs:** `docs/design/design-system.md` solo si se agrega patrón (no previsto).

## Implementation steps
1. Accounting: `account_overrides` + `validate_posting_account` + `posting_options` con pruebas (INV-03, EDGE-01..03).
2. Expenses dominio: `is_posted`, bloqueo en `update`, errores nuevos (INV-05, AC-08).
3. Migración `0004`: `expense_account_id`, `payment_account_id`, `idempotency_key`, índice único `(company_id, idempotency_key)` parcial; mapper y repositorio.
4. Puerto + adaptador; `CreateExpense` (cuentas, huella, post en transacción, sin clasificación obligatoria) (AC-01..07, INV-01..04, INV-07).
5. `VoidExpense` con reversión (AC-09, AC-10, INV-06).
6. API: serializers, `posting-options`, mapeo de errores 400/409 (API-01..04).
7. Frontend: modelos, servicio, formulario con bloque y vista previa, detalle, i18n (UI-01..03, AC-12).
8. Pruebas de regresión y de límites; actualizar `docs/architecture/ddd.md` solo si cambia la convención.

## Database / migrations
Migración nueva `expenses/0004_posting_accounts_idempotency`: columnas nulas e índice único condicionado a `idempotency_key IS NOT NULL`; sin backfill; inversa limpia.

## Risks
Contrato extendido de `post_automatic_entry` (mitigado: parámetro opcional); clasificación ya no exigida (registrado en TASK); concurrencia (índice único + `IntegrityError` → devolver existente).

## New dependencies
Ninguna.
