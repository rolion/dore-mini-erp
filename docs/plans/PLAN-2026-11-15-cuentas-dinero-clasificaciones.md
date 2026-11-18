# PLAN-2026-11-15-cuentas-dinero-clasificaciones (v1)

**Task:** TASK-cuentas-dinero-clasificaciones · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-cuentas-dinero-clasificaciones-pestanas-cuentas-clasificaciones · ADR-cuentas-dinero-clasificaciones-modelo-y-contrato

## Objective
Separar la cuenta de dinero (dónde) de la clasificación (por qué) en Contabilidad: tipo de cuenta, catálogo de clasificaciones de ingreso/egreso por empresa y fachada de validación, sin alterar los ingresos existentes.

## Context
Ver TASK. La cuenta ya admite ambas direcciones; faltan tipo y clasificaciones.

# Specification

## Domain context
Bounded context `accounting`. Consumidores futuros: `expenses`, `purchases` (vía `accounting.services`). `sales`/`receivables` no cambian.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Cuenta de dinero | Lugar donde se mueve el dinero (Caja, Banco, Billetera) | `Account`, tarjeta CONT-01 |
| Tipo de cuenta | `CASH`/`BANK`/`WALLET` | Nuevo |
| Clasificación | Motivo del movimiento, de ingreso o de egreso | Nuevo |
| Método de pago | CASH/QR/BANK_TRANSFER/CARD/OTHER | `catalog.py:6` |
Inconsistencia declarada: «Efectivo» (método) vs «Caja» (tipo de cuenta) son conceptos distintos.

## Current behavior
Ver TASK → Hechos encontrados (`models.py:8-76`, `use_cases.py:90-105`, `services.py:88-113`).

## Expected behavior
- Una cuenta tiene tipo opcional-legado y se usa indistintamente para cobros y pagos.
- Las clasificaciones existen por empresa con dirección ingreso/egreso y se activan/desactivan.
- Otros módulos validan una cuenta o clasificación mediante la fachada.
- Entradas, saldos y referencias de cobros existentes no cambian.

## Domain rules / invariants
- INV-01 (existente) nombre de cuenta único por empresa sin distinguir mayúsculas.
- INV-02 (nueva) `kind ∈ {CASH, BANK, WALLET}` o nulo solo en filas legadas; el alta lo exige.
- INV-03 (nueva) nombre de clasificación 1..80 caracteres, único por `(empresa, nombre sin mayúsculas, dirección)`.
- INV-04 (nueva) `direction ∈ {INCOME, EXPENSE}` e inmutable tras crear.
- INV-05 (nueva) una cuenta o clasificación inactiva o de otra empresa no es válida para usos nuevos; no se borra ni se altera lo ya registrado.
- INV-06 (existente) la cuenta no se desactiva si métodos activos la usan.

## Acceptance criteria
- AC-01: la misma cuenta de tipo Banco supera `validate_money_account` para un uso de cobro (`record_entry`) y para un uso de pago (validación de egreso) sin restricción de dirección.
- AC-02: cuenta o clasificación de otra empresa → rechazo por API (404 en detalle/activar/desactivar) y por fachada (`AccountValidationError`).
- AC-03: desactivar una clasificación o cuenta impide usos nuevos (fachada rechaza) y conserva sus entradas/historial.
- AC-04: los cobros existentes de ventas y servicios conservan referencias y montos tras la migración y la adaptación (regresión de `test_unified_journey` y pagos de Ventas/Cobros).
- AC-05: crear cuenta exige tipo válido; cuentas legadas sin tipo siguen listándose y editándose.
- AC-06: clasificaciones se crean, renombran, filtran por dirección/estado y no permiten duplicados por empresa+dirección.
- AC-07: método de pago, cuenta y clasificación se mantienen como campos distintos en el contrato.

## Edge cases / Error cases
EDGE-01 tipo inválido → 400. EDGE-02 duplicado concurrente → restricción única → 400. EDGE-03 `PATCH` con `direction` → ignorado/400. EDGE-04 dirección incorrecta en `validate_classification` → error de validación.

## Authorization / permissions
Administrador de empresa (`CompanyAdminPermission`); `company_id` siempre del usuario autenticado.

## API contract
- API-01 `GET/POST /api/accounting/accounts/`: respuesta añade `kind` (nullable); alta exige `kind`.
- API-02 `PATCH /api/accounting/accounts/<id>/`: acepta `kind`.
- API-03 `GET/POST /api/accounting/classifications/` (`?direction=`, `?active=`).
- API-04 `GET/PATCH /api/accounting/classifications/<id>/` (PATCH solo `name`).
- API-05 `POST …/classifications/<id>/activate|deactivate/`.
Compatibilidad: lectura de cuentas retrocompatible; el alta de cuentas pasa a exigir `kind` (ver ADR).

## UI behavior
- UI-01 pestaña Cuentas: columna «Tipo» y selector en el diálogo (plantilla «listados en pestañas y diálogo»).
- UI-02 pestaña Clasificaciones con filtros de dirección y estado, diálogo de alta/edición, activar/desactivar.
- UI-03 estados cargando/vacío/error/éxito; textos con claves i18n es/en/pt.

## Non-functional requirements
Sin float en dinero (no se toca dinero). Migración aditiva.

## Out of scope
Partida doble, valoración de inventario, saldos, enlazar entradas/gastos a clasificaciones, migrar `ExpenseCategory`, sembrar clasificaciones, registrar pagos/egresos en Contabilidad.

## Open questions
Unificación con `ExpenseCategory` y enlace de entradas a clasificaciones: tareas posteriores del tablero (no bloquean).

# Test Specification

## Unit tests
Dominio: `Account` con tipo (INV-02), `Classification` (INV-03, INV-04, activar/desactivar).

## Integration tests
API de cuentas con `kind` y de clasificaciones (aislamiento entre dos empresas, filtros, duplicados, activar/desactivar); fachada `validate_*`; migración `0004` con datos previos (`test_migrations`-style: filas existentes quedan con `kind` nulo).

## E2E
**NO** — configuración sin flujo crítico de punta a punta; specs de componentes del frontend (`provideTestTranslations()`).

## Regression tests
`accounting/tests/test_unified_journey.py`, `test_entries_api.py`, pagos de Ventas y Cobros, `npm run i18n:check`, paridad de claves.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | integración fachada + `record_entry` con la misma cuenta |
| AC-02 | integración API/fachada con dos empresas |
| AC-03 | integración: desactivar → rechazo nuevo y entradas intactas |
| AC-04 | regresión `test_unified_journey` + test de migración sobre entradas |
| AC-05 | unit dominio + API alta/legacy |
| AC-06 | integración API clasificaciones |
| AC-07 | test de contrato de serializers (campos distintos) |
| UI-01..03 | specs de `accounts-tab`, `classifications-tab`, `account-dialog` |

# Implementation Plan

## Architecture considerations
DDD pragmático del módulo `accounting`; fachada `services.py` como único punto entre módulos; repositorios con `company_id`.

## Proposed solution
Ver ADR decisiones 1-6.

## Files/components affected
Backend: `accounting/domain/{account.py,classification.py,catalog.py}`, `application/use_cases.py`, `infrastructure/django/{models,repositories}.py`, `api/{serializers,views,urls}.py`, `services.py`, migración `0004`, tests. Frontend: `features/accounting/{models,services,components/classifications-tab,components/classification-dialog,components/account-dialog,components/accounts-tab,pages/accounting-settings}`, i18n es/en/pt. Docs: TASK/ADR/DDR.

## Implementation steps
1. Dominio: `kind` en `Account` y `Classification` (INV-02..04).
2. Modelos + migración `0004` (`kind` anulable, `accounting_classification`).
3. Repositorios y casos de uso (CRUD, filtros, activar/desactivar).
4. API y serializers (API-01..05).
5. Fachada `validate_money_account` / `validate_classification` (AC-01..03).
6. Pruebas backend y regresión (AC-01..07).
7. Frontend: modelos, servicio, pestaña y diálogo de clasificaciones, tipo en cuentas, i18n (UI-01..03).
8. `npm run lint`, `i18n:check`, `npm test`, `manage.py test`.

## Database / migrations
Migración nueva `0004` aditiva; no se edita ninguna aplicada. Rollback con `migrate accounting 0003`.

## Risks
Convivencia con `ExpenseCategory`; cuentas legadas sin tipo; alta de cuentas ahora exige `kind`.

## New dependencies
Ninguna.
