# PLAN-2026-11-16-administrar-cuentas-codigo-clasificacion-estado (v1)

**Task:** TASK-administrar-cuentas-codigo-clasificacion-estado · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** [DDR](../design/DDR-administrar-cuentas-codigo-clasificacion-estado-lista-y-formulario-de-cuentas.md) · [ADR](../adr/ADR-administrar-cuentas-codigo-clasificacion-estado-modelo-de-cuenta.md)

## Objective
Administrar el plan de cuentas de la empresa: cuentas con código único, nombre, clasificación obligatoria y estado, con tipo de dinero opcional y marca de cuenta correctora, sin borrado y sin alterar históricos.

## Context
Tarjeta CONT-09; depende de CONT-08 (PR #79). El plan de cuentas de 40 cuentas **no se carga aquí**.

# Specification

## Domain context
Bounded context `accounting`.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Cuenta | Elemento del plan contable de una empresa, con código, nombre y clasificación | Tarjeta CONT-09 |
| Cuenta de dinero | Cuenta de Activo con tipo Caja/Banco/Billetera | CONT-01, ADR |
| Cuenta correctora | Cuenta cuyo saldo normal es contrario al de su clasificación (p. ej. Depreciación acumulada) | Aclaración del dueño |
| Asientos | Hoy, entradas del libro de la cuenta; luego, líneas de asiento (CONT-02) | ADR |

## Current behavior
Sin código; `kind` obligatorio al crear (`api/serializers.py:16-20`); clasificación opcional; sin cuenta correctora; bloqueos por entradas solo en moneda y apertura (`use_cases.py:90,102`).

## Expected behavior
- Crear exige código, nombre y clasificación habilitada; `kind` opcional y solo con Activo; `is_contra` opcional.
- El código es único por empresa (sin distinguir mayúsculas) y distintas empresas pueden repetirlo.
- Cambiar la clasificación o `is_contra` exige que no haya asientos; renombrar y cambiar el código siempre se puede.
- Deshabilitar y habilitar no borran; deshabilitar con métodos activos devuelve el 409 actual; no existe borrado.
- Las cuentas inactivas siguen en listados y saldos y no se aceptan para usos nuevos.

## Domain rules / invariants
- INV-01: `code` obligatorio al crear, recortado, 1-20 caracteres de `[A-Za-z0-9._-]`.
- INV-02: `(company_id, lower(code))` único cuando `code` no es nulo.
- INV-03: `account_class` obligatoria al crear, del catálogo y habilitada (nuevo valor).
- INV-04: `kind` solo si `account_class` = `ASSET`.
- INV-05: con asientos, `account_class` e `is_contra` no cambian.
- INV-06: sin borrado de cuentas.
- INV-07 (existente): desactivar una cuenta usada por métodos activos se rechaza.

## Acceptance criteria
- AC-01: crear `101` / `Caja` / Activo funciona; el mismo código en la misma empresa (también en otra capitalización) da 400 en `code`; en otra empresa se acepta.
- AC-02: crear sin código o sin clasificación da 400 en el campo; con clasificación deshabilitada da 400 en `account_class`.
- AC-03: deshabilitar Caja la quita de los selectores de usos nuevos (`validate_money_account` la rechaza) y mantiene sus entradas y su saldo; sigue en el listado.
- AC-04: con entradas, cambiar la clasificación da 409 `account_has_entries`; cambiar el nombre da 200 y las entradas siguen idénticas.
- AC-05: `kind` con una clasificación distinta de Activo da 400 en `kind`; Caja (Activo) con `kind` y Gastos sin `kind` se aceptan.
- AC-06: una cuenta marcada `is_contra` (Activo, «Depreciación acumulada») se crea y se lista con el indicador; con asientos, cambiar `is_contra` da 409.
- AC-07: no existen rutas de borrado (405/404).
- AC-08: una cuenta anterior sin código ni clasificación sigue en el listado, operativa, y puede completarse con un PATCH.
- AC-09: desactivar una cuenta usada por un método activo sigue devolviendo 409 `account_in_use` con los métodos.
- AC-10: aislamiento: una empresa no ve ni modifica las cuentas de otra; el listado acepta `?account_class=` y ordena por código.
- AC-11: la migración `0008` sobre una base con cuentas conserva sus datos y es reversible.
- AC-12: UI: lista con código y clasificación, filtro por clasificación, diálogo con las reglas del DDR y solo clasificaciones habilitadas.

## Edge cases / Error cases
- `account_class: null` en PATCH no cambia nada.
- Código con espacios internos o caracteres no permitidos: 400.
- Carrera al crear dos cuentas con el mismo código: gana la restricción única (400, no 500).
- Cambiar la clasificación de Activo a otra con `kind` presente: 400 en `kind`.

## Authorization / permissions
Mismos permisos que la configuración de Contabilidad (`_ConfigView`, administrador de la empresa; `required_modules = ()`).

## API contract
- API-01: `POST/PATCH /api/accounting/accounts/` aceptan `code`, `account_class`, `is_contra`, `kind` (opcional).
- API-02: `GET` devuelve `code`, `account_class`, `is_contra`, `kind`; filtro `?account_class=`; orden por código.
- API-03: errores 400 por campo; 409 `account_has_entries` y `account_in_use`.
- Compatibilidad: el alta pasa a exigir `code` y `account_class` (único cliente: el panel, actualizado en el mismo PR).

## UI behavior
- UI-01: lista según el DDR (columnas, filtro, etiqueta «Correctora», «Sin código»).
- UI-02: diálogo con código, nombre, clasificación (solo habilitadas), cuenta de dinero (solo con Activo) y casilla correctora; campos bloqueados con asientos.
- UI-03: estados cargando/vacío/error/éxito y textos es/en/pt.

## Non-functional requirements
Consultas por `company_id`; sin `float`; sin texto hardcodeado.

## Out of scope
Cargar el plan de 40 cuentas; restringir el destino de los métodos a cuentas de dinero (CONT-12); asientos con líneas y su bloqueo (CONT-02); saldos por cuenta (CONT-04); períodos (CONT-10).

## Open questions
Ninguna bloqueante.

# Test Specification

## Unit tests
Dominio: validación del código (INV-01), `kind` solo con Activo (INV-04), `is_contra`.

## Integration tests
API con dos empresas: AC-01 a AC-10; migración con datos (AC-11).

## E2E
**NO** — sin flujo crítico de punta a punta; la UI se cubre con pruebas de componente.

## Regression tests
`modules.accounting` completo, `test_boundaries`, `makemigrations --check`, `ng test`, `ng lint`, `i18n:check`, `ng build`.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01, AC-02 | Integración API (códigos repetidos y capitalización, otra empresa, campos faltantes, clasificación deshabilitada) |
| AC-03 | Integración: fachada + entradas y saldo antes/después |
| AC-04 | Integración: 409 con entradas y renombrar OK |
| AC-05 | Unitaria del dominio e integración API |
| AC-06 | Integración API con entradas |
| AC-07 | Integración: métodos no permitidos |
| AC-08 | Integración con cuenta creada por el repositorio sin código |
| AC-09 | Integración con un método mapeado |
| AC-10 | Integración: aislamiento, filtro y orden |
| AC-11 | Prueba de migración con datos y reversión |
| AC-12 | Pruebas de componente de lista y diálogo y del servicio |

# Implementation Plan

## Architecture considerations
DDD como `ddd.md`: reglas en el dominio (`Account`), casos de uso `CreateAccount`/`UpdateAccount`, repositorio con `company_id`.

## Proposed solution
Ver ADR.

## Files/components affected
- Backend: `domain/account.py`, `application/use_cases.py`, `infrastructure/django/models.py` y `repositories.py`, `api/serializers.py|views.py`, migración `0008`, tests.
- Frontend: `accounts-tab`, `account-dialog`, `models/accounting.ts`, `accounting-api.service.ts`, `assets/i18n/{es,en,pt}.json`.

## Implementation steps
1. Dominio: código, `is_contra`, regla de `kind` y bloqueo (INV-01, INV-04, INV-05) con pruebas.
2. Modelo, migración `0008` y repositorio con unicidad insensible a mayúsculas (INV-02).
3. Casos de uso: alta obligatoria, edición con bloqueos, 409 (AC-01..AC-06, AC-08, AC-09).
4. API: campos, filtro y orden (API-01..03; AC-07, AC-10).
5. Pruebas de integración y de migración.
6. Frontend: modelo, servicio, lista y diálogo con i18n (UI-01..03; AC-12).
7. Verificación completa y regresiones.

## Database / migrations
`0008`: `code`, `is_contra` y restricción única parcial. Aditiva; rollback `migrate accounting 0007`.

## Risks
- Cambio del contrato de alta (mitigado: mismo PR para el cliente).
- Selector de métodos con cuentas que no son de dinero hasta CONT-12.
- El bloqueo por asientos usa entradas hasta CONT-02.

## New dependencies
Ninguna.
