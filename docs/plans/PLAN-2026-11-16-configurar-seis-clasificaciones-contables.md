# PLAN-2026-11-16-configurar-seis-clasificaciones-contables (v1)

**Task:** TASK-configurar-seis-clasificaciones-contables · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** [DDR](../design/DDR-configurar-seis-clasificaciones-contables-pestana-de-configuracion.md) · [ADR](../adr/ADR-configurar-seis-clasificaciones-contables-catalogo-fijo-y-validacion.md)

## Objective
Cada empresa dispone de las seis clasificaciones contables fijas y puede habilitarlas o deshabilitarlas; una deshabilitada no se acepta para cuentas nuevas ni en la API, y nada existente cambia.

## Context
Tarjeta CONT-08; antecedente CONT-07 (PR #78). Base `accounting`. CONT-09 consumirá la fachada.

# Specification

## Domain context
Bounded context `accounting`. Sin otros módulos.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Clasificación contable | Una de seis: Activo, Pasivo, Patrimonio, Ingresos, Gastos, Costos | Tarjeta CONT-08 |
| Habilitada/deshabilitada | Estado por empresa; ausencia de registro = habilitada | ADR decisión 2 |
| Clasificación (CONT-01) | Motivo de un movimiento INCOME/EXPENSE; **otro concepto** | `models.py:60` |

## Current behavior
La cuenta no tiene clasificación contable (`domain/account.py:78-89`); el catálogo CONT-01 es libre y por dirección.

## Expected behavior
- `GET /api/accounting/account-classes/` devuelve siempre exactamente seis, en orden fijo, con `enabled`.
- Habilitar/deshabilitar por empresa; sin crear/renombrar/borrar.
- Crear/editar cuenta con `account_class`: se acepta solo si está habilitada (salvo que sea el valor que la cuenta ya tiene).
- Deshabilitar no toca cuentas, entradas ni saldos.

## Domain rules / invariants
- INV-01 (nueva): el catálogo son exactamente `ASSET, LIABILITY, EQUITY, INCOME, EXPENSE, COST`.
- INV-02: el estado es por `(company_id, code)`; ausencia = habilitada.
- INV-03: deshabilitar es solo-escritura de su fila; ninguna otra tabla cambia.
- INV-04: una cuenta con clasificación deshabilitada conserva su valor y sigue operando según su `is_active`.

## Acceptance criteria
- AC-01: la lista contiene exactamente las seis (incluida Ingresos), en orden fijo, también para una empresa sin registros.
- AC-02: deshabilitar Costos en A: crear/editar a Costos en A → 400 `account_class`; en B sigue permitido.
- AC-03: una cuenta existente de Costos en A conserva `account_class`, sus entradas y saldo (`account_balances`), y puede renombrarse/operar según su `is_active`.
- AC-04: no existen rutas ni casos de uso para crear, renombrar o borrar (405/404).
- AC-05: habilitar/deshabilitar es idempotente; reintentar no duplica filas; código desconocido → 404.
- AC-06: usuario sin permiso de administración → 403; usuario de otra empresa no ve ni cambia el estado de A.
- AC-07: UI: pestaña «Clasificaciones contables» con las seis y su estado; el diálogo de cuenta ofrece solo habilitadas.
- AC-08: `migrate` desde cero y sobre una copia con datos aplica `0007` sin alterar filas existentes.

## Edge cases / Error cases
- Deshabilitar las seis: permitido; cuentas nuevas sin clasificación siguen posibles (`account_class` es opcional hasta CONT-09).
- Enviar `account_class` con código inválido o en minúsculas: 400 (se normaliza a mayúsculas solo si coincide con el catálogo).
- Cuenta con clasificación deshabilitada que se edita sin cambiar la clasificación: se acepta.

## Authorization / permissions
Mismos permisos y gate que el resto de la configuración (`_ConfigView`, `required_modules = ()`).

## API contract
- API-01: `GET /api/accounting/account-classes/` → `[{code, enabled}]` (6 elementos).
- API-02: `POST /api/accounting/account-classes/<code>/enable/` y `/disable/` → `{code, enabled}`.
- API-03: `account_class` opcional (nullable) en `POST/PATCH /api/accounting/accounts/` y en la respuesta; retrocompatible.

## UI behavior
- UI-01: pestaña «Clasificaciones contables» según plantilla de configuración con listados (DDR); botón de texto por fila; estados cargando/error/éxito.
- UI-02: selector opcional en `account-dialog` con solo las habilitadas (la actual de la cuenta aparece marcada «deshabilitada» si procede).
- UI-03: textos en es/en/pt.

## Non-functional requirements
Consultas filtradas por `company_id`; sin `float`; sin texto hardcodeado.

## Out of scope
Código de cuenta, clasificación obligatoria, bloqueo de cambio por asientos (CONT-09); retirada de la pestaña CONT-01 (CONT-11); asientos, conversión y migración de datos (CONT-02/07 Etapa 2).

## Open questions
Ninguna bloqueante.

# Test Specification

## Unit tests
Dominio: catálogo exacto y orden (INV-01), normalización/validación de código.

## Integration tests
API y fachada con dos empresas: AC-01, AC-02, AC-03 (cuenta con entradas y saldo antes/después), AC-04, AC-05, AC-06; migración (AC-08) vía creación de la base de pruebas y prueba de `0007` con datos previos.

## E2E
**NO** — sin flujo crítico de punta a punta; la UI se cubre con pruebas de componente (Karma) y `i18n:check`.

## Regression tests
`modules.accounting` completo, `test_boundaries`, `makemigrations --check`, `npm test` del feature `accounting`, `npm run lint`, `npm run i18n:check`.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | Integración API + unitaria del catálogo |
| AC-02 | Integración API dos empresas |
| AC-03 | Integración: cuenta con entradas, saldo igual tras deshabilitar |
| AC-04 | Integración: métodos no permitidos |
| AC-05 | Integración: doble habilitar/deshabilitar, una fila |
| AC-06 | Integración: 403 y aislamiento |
| AC-07 | Pruebas de componente de la pestaña y del diálogo |
| AC-08 | Prueba de migración con datos + base nueva |

# Implementation Plan

## Architecture considerations
DDD como `ddd.md`: dominio puro, caso de uso, repositorio `Django…Repository(company_id)`, fachada en `services.py`.

## Proposed solution
Ver ADR: catálogo en dominio, tabla de excepciones (deshabilitadas), columna nulable en la cuenta, fachada y API.

## Files/components affected
- Backend: `domain/account_class.py` (nuevo), `domain/account.py`, `application/use_cases.py`, `infrastructure/django/models.py` y `repositories.py`, `services.py`, `api/serializers.py|views.py|urls.py`, migración `0007`, tests nuevos.
- Frontend: `components/account-classes-tab/` (nuevo), `accounting-settings` (pestaña), `account-dialog`, `models/accounting.ts`, `accounting-api.service.ts`, `assets/i18n/{es,en,pt}.json`.
- Docs: este PLAN, TASK, ADR, DDR.

## Implementation steps
1. Dominio: catálogo y validación de código (INV-01) + pruebas.
2. Modelo, migración `0007` y repositorio (INV-02/03).
3. Casos de uso `ListAccountClasses`, `SetAccountClassEnabled`; fachada `validate_account_class`.
4. API de clasificaciones (API-01/02) y `account_class` en cuentas (API-03; AC-02..06).
5. Pruebas de integración y de migración (AC-03, AC-08).
6. Frontend: servicio, pestaña y selector del diálogo con i18n (UI-01..03; AC-07).
7. Verificación completa y regresiones.

## Database / migrations
`0007`: crea `accounting_account_class_setting` y agrega `accounting_account.account_class` nulable. Aditiva; no se editan migraciones previas; rollback `migrate accounting 0006`.

## Risks
- Confusión entre los dos catálogos: mitigada en nombres, textos de ayuda y ADR.
- Retrocompatibilidad del API de cuentas: el campo es opcional.

## New dependencies
Ninguna.
