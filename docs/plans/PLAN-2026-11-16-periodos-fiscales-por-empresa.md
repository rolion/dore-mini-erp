# PLAN-2026-11-16-periodos-fiscales-por-empresa (v1)

**Task:** TASK-periodos-fiscales-por-empresa · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-periodos-fiscales-por-empresa-pestana-periodos-fiscales · ADR-periodos-fiscales-por-empresa-agregado-y-bloqueo

## Objective
Permitir a la persona administradora crear, editar, cerrar y reabrir períodos fiscales por empresa, y dejar en `accounting.services` el contrato de bloqueo que el motor de asientos (CONT-02) usará para exigir fecha en período abierto sin carreras con el cierre.

## Context
Ver `docs/tasks/TASK-periodos-fiscales-por-empresa.md`. Hoy no existen períodos ni asientos; los cobros actuales (`record_entry`) no cambian.

# Specification

## Domain context
Bounded context `accounting`. Sin dependencias nuevas con otros módulos.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Período fiscal | Rango de fechas inclusivo `[inicio, fin]` de una empresa, con estado | Trello CONT-10 |
| Abierto / Cerrado | Estado; solo en un período abierto se contabilizan asientos | Trello CONT-10 |
| Fecha contable | Fecha del asiento (CONT-02) que debe caer en un período abierto | Trello CONT-02/10 |

## Current behavior
No hay períodos (`backend/modules/accounting/`, sin `FiscalPeriod`). Contrato análogo: `services.py:88` (`record_entry`).

## Expected behavior
Administrar períodos desde Contabilidad › Configuración › Períodos fiscales y exponer `lock_open_period` / `period_for` en la fachada.

## Domain rules / invariants
- INV-01: nombre de 1 a 80 caracteres, único por empresa sin distinguir mayúsculas.
- INV-02: `inicio ≤ fin`; fechas inclusivas.
- INV-03: dos períodos de la misma empresa no se superponen (compartir un día es superposición); empresas distintas pueden tener rangos idénticos.
- INV-04: un período nuevo nace abierto. Cerrar y reabrir son transiciones explícitas del agregado; cerrar un cerrado o reabrir un abierto es error.
- INV-05: un período cerrado no cambia nombre ni límites.
- INV-06: cambiar límites no puede dejar fuera del período ningún asiento hoy dentro de él.
- INV-07: cerrar no crea asientos ni ningún otro registro contable.
- INV-08: contabilizar una fecha exige un período abierto de la empresa que la contenga; con cierre simultáneo, nunca queda un asiento insertado tras el cierre.

## Acceptance criteria
- AC-01: crear período válido (queda abierto) y listar ordenado por inicio descendente.
- AC-02: rechazar `inicio > fin`, nombre vacío/largo, fechas inválidas y nombre duplicado (400 por campo).
- AC-03: rechazar solapamientos (contenido, contenedor, parcial, idéntico, un día compartido) con 409 `period_overlap`; permitir períodos contiguos (fin D / inicio D+1).
- AC-04: mismos rangos y nombres en empresas distintas; lista/detalle/acciones de otra empresa responden 404.
- AC-05: cerrar y reabrir (estados, usuario y fecha registrados); cerrado rechaza editar (409 `period_closed`); transición inválida 409 `period_invalid_state`; cerrar no crea asientos.
- AC-06: `lock_open_period` acepta fecha en período abierto; rechaza fecha sin período (`DateOutsideFiscalPeriod`) y en período cerrado (`FiscalPeriodClosed`); una fecha explícita en un período abierto se acepta aunque el período del original esté cerrado (reversión).
- AC-07: `lock_open_period` fuera de transacción falla con `FiscalPeriodContractError`.
- AC-08: cambiar límites se rechaza (409 `period_has_entries`) si el puerto de uso reporta asientos que quedarían fuera; se permite si siguen cubiertos.
- AC-09: cierre concurrente con contabilización: tras ambos, o el asiento existe y el cierre ocurrió después, o el asiento fue rechazado; jamás hay asiento posterior al cierre. Creación concurrente de dos períodos solapados de la misma empresa: solo uno persiste.
- AC-10: UI de la pestaña (listar, crear, editar, cerrar, reabrir) con estados cargando/vacío/error/éxito, errores del servidor en el diálogo y textos i18n es/en/pt.

## Edge cases / Error cases
- Período que cubre un solo día; fechas fuera del rango de `date` válido (rechazo por serializer).
- Dos clics en «Cerrar»: el segundo recibe 409 `period_invalid_state`.
- Huecos entre períodos: fechas en el hueco se rechazan al contabilizar.
- Período sin asientos cerrado y reabierto repetidamente: permitido.

## Authorization / permissions
Permiso por defecto de la API (rol admin de empresa activa); cerrar y reabrir igual. No hay permiso nuevo. Empresa siempre del usuario autenticado.

## API contract
- API-01: `GET /api/accounting/fiscal-periods/` → lista (`id, name, start_date, end_date, status, closed_at, closed_by_name, reopened_at, reopened_by_name`).
- API-02: `POST` mismo recurso `{name, start_date, end_date}` → 201.
- API-03: `GET|PATCH /api/accounting/fiscal-periods/<id>/` (PATCH parcial de `name`, `start_date`, `end_date`).
- API-04: `POST .../<id>/close/` y `.../<id>/reopen/` → 200 con el período.
- API-05: errores 400 por campo; 409 `{detail, code, periods?}` con los códigos del ADR. `required_modules = ()`. Sin cambios a endpoints existentes.

## UI behavior
- UI-01: pestaña «Períodos fiscales» (patrón «Configuración con listados en pestañas y diálogo», design-system §5) con tabla, badge de estado y acciones por estado.
- UI-02: diálogos de período y de confirmación cerrar/reabrir según DDR.

## Non-functional requirements
Dinero no interviene. Fechas como `date` sin zona horaria. Índices por `(company_id, start_date)`. Sin dependencias nuevas.

## Out of scope
- Motor de asientos, reversión y adaptador real de `PeriodUsage` (CONT-02); menú reorganizado y Clasificaciones (CONT-08/11).
- Exigir período a `record_entry` (decisión de la persona).
- Eliminar períodos, asistente de creación de año completo, cierre de resultados.

## Open questions
- Ninguna que bloquee. CONT-02 debe cablear el adaptador de `PeriodUsage` y probar AC-08/AC-09 con asientos reales.

# Test Specification

## Unit tests
- Dominio `FiscalPeriod` (INV-01..05): creación, límites, close/reopen, inmutabilidad (sin base de datos).
- Casos de uso con repositorio en memoria/puerto simulado: solapamiento (AC-03), puerto de uso (AC-08).

## Integration tests
- API (APITestCase): AC-01, AC-02, AC-03, AC-04, AC-05, permisos (no admin 403, sin empresa 403).
- Fachada `lock_open_period` / `period_for`: AC-06, AC-07.
- Concurrencia (`TransactionTestCase`, `_run_together`): AC-09 (cierre vs. inserción de una fila de prueba bajo `lock_open_period`; dos altas solapadas).
- Frontend (Karma): servicio API, componente de pestaña y diálogos con `provideTestTranslations()`; paridad i18n (prueba existente) y `npm run i18n:check`.

## E2E
**NO** — sin flujo crítico de punta a punta nuevo; la integración con asientos reales se valida en CONT-02/CONT-13.

## Regression tests
Suite completa de `accounting` y `modularity` (migración nueva, `makemigrations --check`).

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | API test crear/listar |
| AC-02 | Unit dominio + API test 400 |
| AC-03 | Unit caso de uso + API test 409 |
| AC-04 | API test dos empresas |
| AC-05 | Unit dominio + API test close/reopen/closed-edit |
| AC-06 | Integration fachada |
| AC-07 | Integration fachada |
| AC-08 | Unit caso de uso con puerto simulado + API test con adaptador sustituido |
| AC-09 | Concurrency tests |
| AC-10 | Karma specs + i18n check |

# Implementation Plan

## Architecture considerations
Seguir ADR: agregado sin Django, repositorio `DjangoFiscalPeriodRepository(company_id)`, bloqueo advisory por empresa para altas/edición de límites, `FOR UPDATE` de la fila para cerrar/reabrir/contabilizar, fachada en `services.py`. Cuidar `__all__` y que los módulos no importen infraestructura entre sí.

## Proposed solution
Ver ADR decisiones 1-8.

## Files/components affected
- Backend: `accounting/domain/fiscal_period.py` (nuevo), `application/fiscal_periods.py` (nuevo; incluye el puerto `PeriodUsage`), `infrastructure/django/models.py` (+`FiscalPeriodModel`), `infrastructure/django/repositories.py` (+repositorio), `infrastructure/adapters.py` (+`NoJournalPeriodUsage`), `api/serializers.py`, `api/views.py`, `api/urls.py`, `services.py` (+`lock_open_period`, `period_for`, `PeriodRef`, excepciones), `migrations/0004_fiscal_period.py`, tests nuevos en `accounting/tests/`.
- Frontend: `features/accounting/models/fiscal-period.ts`, `services/fiscal-periods-api.service.ts`, `components/periods-tab`, `components/period-dialog`, `components/period-status-dialog`, `pages/accounting-settings` (tercera pestaña), `testing/fiscal-period-fixtures.ts`, `assets/i18n/{es,en,pt}.json`.
- Docs: nota en `docs/architecture/ddd.md` (módulo accounting).

## Implementation steps
1. Dominio `FiscalPeriod` + errores y pruebas unitarias (INV-01..05, AC-02, AC-05).
2. Modelo, migración `0009`, repositorio con bloqueo advisory y `FOR UPDATE` (INV-03, INV-08).
3. Casos de uso: crear, editar, cerrar, reabrir, listar, obtener, con puerto `PeriodUsage` (AC-01, AC-03, AC-05, AC-08).
4. Fachada `lock_open_period`/`period_for` y pruebas (AC-06, AC-07).
5. API, serializers, URLs y pruebas (AC-01..05, permisos).
6. Pruebas de concurrencia (AC-09).
7. Frontend: modelo, servicio, pestaña, diálogos, i18n y specs (AC-10).
8. Actualizar `ddd.md`; suite backend + `npm test`, `npm run lint`, `npm run i18n:check`, `npm run build`.

## Database / migrations
Migración nueva `0009_fiscal_period` (tabla, checks, único `(company_id, lower(name))`, índice). No toca migraciones aplicadas. (Nota v1: al integrar la rama `accounting` la migración quedó como `0009_fiscal_period`, dependiente de `0008`.)

## Risks
- Bloqueo advisory: usar el patrón de namespace de `adapters.py` y liberarlo con `xact` (fin de transacción) para no filtrar bloqueos.
- Pruebas de concurrencia requieren `TransactionTestCase` y PostgreSQL.
- Adaptador real de `PeriodUsage` pendiente de CONT-02.

## New dependencies
Ninguna.
