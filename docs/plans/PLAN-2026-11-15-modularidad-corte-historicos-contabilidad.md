# PLAN-2026-11-15-modularidad-corte-historicos-contabilidad (v1)

**Task:** TASK-modularidad-corte-historicos-contabilidad · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-modularidad-corte-historicos-contabilidad-corte-apertura-cobertura · ADR-modularidad-corte-historicos-contabilidad-ciclo-de-vida-y-corte

## Objective
Dejar a Contabilidad lista para recibir egresos sin romper a Gastos ni Compras: fecha de corte por empresa, saldo de apertura por cuenta, periodos sin cobertura, bloqueo al deshabilitar con egresos vigentes, decisión única «¿se registra movimiento?» y catálogo de módulos sin la dependencia innecesaria Compras → Gastos.

## Context
Ver TASK. La base de CONT-01 (rama actual, PR 74) aporta cuentas con tipo y clasificaciones. Los movimientos de egreso aún no existen (CONT-02).

# Specification

## Domain context
`accounting` (ajustes, cobertura, apertura, fachada) y `modularity` (ciclo de vida, catálogo). `expenses`/`purchases` solo cambian de catálogo; consumirán la fachada en GAS-01/COM-01.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Fecha de corte | Día desde el cual Contabilidad cuenta los movimientos de una empresa | Tarjeta CONT-06, decisión del usuario |
| Saldo de apertura | Monto de una cuenta a la fecha de corte | Decisión del usuario |
| Periodo sin cobertura | Intervalo en que Contabilidad estuvo deshabilitada tras el corte | Decisión del usuario |
| Cobertura | La operación tiene fecha ≥ corte, Contabilidad habilitada y fuera de un periodo sin cobertura | ADR decisión 5 |
Inconsistencia declarada: «habilitada» (módulo) ≠ «cubierta» (fecha efectiva).

## Current behavior
Ver TASK → Hechos (`modules.py:30-43`, `use_cases.py:46-80`, `views.py:73-90`, `models.py`, `repositories.py:214,243`, `sales/infrastructure/adapters.py:178-198`).

## Expected behavior
- Habilitar Contabilidad crea una vez el ajuste de corte (hoy) y abre un periodo; repetir no duplica nada ni mueve el corte.
- Deshabilitar cierra el periodo; reactivar abre otro y el hueco queda como periodo sin cobertura; no se crean movimientos retroactivos.
- Deshabilitar se rechaza si hay egresos vigentes sin revertir.
- Gastos y pagos de Compras funcionan con Contabilidad deshabilitada y sin movimientos; anular un gasto sin movimiento no toca saldos.
- Cada cuenta tiene un saldo de apertura a la fecha de corte.
- El libro y la configuración muestran la cobertura parcial.
- Compras ya no requiere Gastos.

## Domain rules / invariants
- INV-01 (nueva) hay a lo sumo un ajuste de corte por empresa y un periodo abierto por empresa.
- INV-02 (nueva) el corte se fija al habilitar por primera vez y solo cambia mientras no haya movimientos; después es inmutable.
- INV-03 (nueva) el saldo de apertura es ≥ 0, `Decimal` con 2 decimales, y solo cambia mientras la cuenta no tiene movimientos.
- INV-04 (nueva) un movimiento solo se crea si hay cobertura; nunca por fecha anterior al corte ni durante un periodo sin cobertura.
- INV-05 (nueva) deshabilitar Contabilidad es imposible mientras haya egresos vigentes sin revertir.
- INV-06 (nueva) `accounting` no depende de `expenses` ni de `purchases`.
- INV-07 (existente) las entradas de ingresos son inmutables y únicas por origen.

## Acceptance criteria
- AC-01: con Contabilidad deshabilitada, registrar un gasto y pagar una compra funciona y no crea movimientos ni exige cuenta (prueba 1 de la tarjeta).
- AC-02: habilitar Contabilidad no cambia gastos, compras ni entradas existentes y no crea movimientos (prueba 2).
- AC-03: repetir habilitar/deshabilitar/habilitar no duplica ajustes, periodos abiertos ni movimientos, y conserva corte y apertura (prueba 3).
- AC-04: las reglas de módulos (requires, 409 de dependencias, bloqueo de deshabilitar) vienen de la API y el frontend las muestra sin reglas propias; Compras se habilita sin Gastos (prueba 4).
- AC-05: anular un gasto anterior al corte (o sin movimiento) no modifica ninguna cuenta ni crea entradas (prueba 5).
- AC-06: el corte se crea con hoy al habilitar, se puede cambiar antes de haber movimientos y queda bloqueado (409 `cutoff_locked`) después.
- AC-07: `coverage_status` devuelve no cubierto para fechas anteriores al corte, con el módulo deshabilitado o dentro de un periodo sin cobertura.
- AC-08: deshabilitar con egresos vigentes responde 409 `disable_blocked` y el módulo sigue habilitado; sin egresos se permite.
- AC-09: el saldo de apertura se guarda por cuenta, se rechaza si es negativo o con más de 2 decimales y no se puede cambiar con movimientos.
- AC-10: el libro de entradas expone `cutoff_date` y `gaps` y el panel muestra el aviso de cobertura parcial.
- AC-11: una empresa con Contabilidad ya habilitada obtiene su corte al primer acceso (primera entrada, o hoy) sin tocar sus entradas.
- AC-12: `accounting` no importa `expenses` ni `purchases` (prueba de fronteras) y no se añaden ciclos.

## Edge cases / Error cases
EDGE-01 fecha de corte futura → 400. EDGE-02 corte cambiado con entradas → 409. EDGE-03 deshabilitar un módulo no habilitado → idempotente. EDGE-04 otra empresa nunca ve ni cambia el corte, la apertura ni los periodos de la primera.

## Authorization / permissions
Administrador de empresa (`CompanyAdminPermission`); `company_id` del usuario.

## API contract
- API-01 `GET /api/accounting/settings/` → `{cutoff_date, enabled_at, locked, gaps:[{from,to}]}` (crea el ajuste perezosamente si falta y el módulo está habilitado; si no está habilitado devuelve `cutoff_date: null`).
- API-02 `PATCH /api/accounting/settings/` `{cutoff_date}` → 200 o 409 `cutoff_locked`.
- API-03 `opening_balance` (string decimal) en `GET/POST/PATCH /api/accounting/accounts/`.
- API-04 `coverage` de `GET /api/accounting/entries/` añade `cutoff_date` y `gaps`.
- API-05 `POST /api/modules/accounting/disable/` puede responder 409 `{code:'disable_blocked', blockers:[…]}`.
- API-06 catálogo: `purchases.requires=['catalog']`, `optional` incluye `expenses`.
Compatibilidad: campos nuevos son aditivos; cambia que Compras se habilita sin Gastos.

## UI behavior
- UI-01 pestaña «Corte y cobertura» (plantilla «listados en pestañas y diálogo»).
- UI-02 «Saldo de apertura» en el diálogo de cuenta y columna en la tabla.
- UI-03 aviso de cobertura parcial en el libro con enlace a la pestaña.
- UI-04 estados cargando/vacío/error/éxito; textos con claves i18n es/en/pt; el 409 `disable_blocked` se muestra en Módulos.

## Non-functional requirements
Dinero en `Decimal`; operaciones de ciclo de vida en la misma transacción que el cambio de módulo; consultas aisladas por `company_id`.

## Out of scope
Registrar egresos, reversiones, saldos calculados y reportes (CONT-02/04/05); asociaciones de categorías (CONT-03); integración de Gastos/Compras (GAS-01/02, COM-01); recontabilizar históricos; cambiar el comportamiento actual de los ingresos; resolver el ciclo accounting ⇄ sales/receivables.

## Open questions
Si un cobro de ventas/servicios con fecha anterior al corte debe generar entrada (hoy sí; no bloquea).

# Test Specification

## Unit tests
Dominio: corte, periodos (abrir/cerrar/huecos), `coverage_status`, validación de apertura, bloqueadores.

## Integration tests
API de módulos (enable/disable con ciclo de vida y 409), API de ajustes y cuentas con apertura (dos empresas), libro con `coverage` ampliado, regresiones de Gastos y pagos de Compras con Contabilidad deshabilitada, prueba de fronteras, migración `0005` con datos previos (cuentas y entradas intactas).

## E2E
**NO** — configuración y reglas de servidor sin flujo crítico de punta a punta; specs de componentes del frontend con `provideTestTranslations()`.

## Regression tests
`accounting` completo, `modularity`, pagos de `sales`/`receivables`, `purchases` y `expenses` completos, `npm run i18n:check`, lint y specs del frontend.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | integración: gasto y pago de compra con Contabilidad deshabilitada, conteo de entradas = 0 |
| AC-02 | integración: habilitar, conteos de gastos/compras/entradas sin cambio |
| AC-03 | integración: ciclo habilitar→deshabilitar→habilitar ×2, un solo ajuste y un periodo abierto |
| AC-04 | integración API de módulos + spec `module-list` (requires de la API) |
| AC-05 | integración: anular gasto previo al corte, saldos/entradas intactos |
| AC-06 | integración API de ajustes (cambiar antes, 409 después) |
| AC-07 | unit + integración de `coverage_status` |
| AC-08 | integración con bloqueador de prueba (409, módulo sigue habilitado; sin bloqueo se permite) |
| AC-09 | unit + API de cuentas |
| AC-10 | integración del libro + spec de `entry-list` |
| AC-11 | integración: empresa con entradas y módulo habilitado sin ajuste |
| AC-12 | prueba de fronteras |
| UI-01..04 | specs de pestaña de corte, diálogo de cuenta, entry-list y module-list |

# Implementation Plan

## Architecture considerations
Puerto neutro `shared/module_lifecycle.py` (patrón de `enable_preconditions`); `modularity` no importa `accounting`; la regla de cobertura vive en el dominio de `accounting`.

## Proposed solution
Ver ADR decisiones 1-8.

## Files/components affected
Backend: `shared/module_lifecycle.py`, `modularity/{domain/modules.py,application/use_cases.py,api/views.py}`, `accounting/{domain,application,infrastructure,api,services.py,apps.py}`, migración `0005`, test de fronteras, tests. Frontend: `features/accounting/{models,services,components,pages}`, `features/settings` (409 de módulos), i18n es/en/pt. Docs: TASK/ADR/DDR/PLAN.

## Implementation steps
1. Catálogo: `purchases` sin `requires expenses`; ajustar tests de `modularity` (AC-04, AC-12).
2. Puerto `module_lifecycle` y su uso en `EnableModule`/`DisableModule` con 409 `disable_blocked` (AC-08).
3. Dominio de corte, periodos y cobertura (INV-01, INV-02, INV-04; AC-06, AC-07).
4. Modelos y migración `0005` (ajustes, periodos, `opening_balance`) (INV-01, INV-03).
5. Casos de uso, registro de ganchos en `apps.py`, `ensure_settings` perezoso (AC-03, AC-11).
6. API de ajustes, apertura en cuentas y `coverage` ampliado (API-01..05; AC-09, AC-10).
7. Fachada `coverage_status` (AC-07).
8. Pruebas de independencia de Gastos/Compras y de fronteras (AC-01, AC-02, AC-05, AC-12).
9. Frontend: pestaña de corte, apertura en cuentas, aviso en el libro, 409 en módulos, i18n (UI-01..04).
10. Correr suites completas, lint e `i18n:check`.

## Database / migrations
Migración nueva `accounting/0005` (dos `CreateModel` y un `AddField` con defecto 0); no se edita ninguna aplicada. Rollback: `migrate accounting 0004`.

## Risks
Ciclo preexistente accounting ⇄ sales/receivables; bloqueo probado con doble hasta CONT-02; cambio de reglas de habilitación de Compras; completar el corte de empresas existentes de forma perezosa.

## New dependencies
Ninguna.
