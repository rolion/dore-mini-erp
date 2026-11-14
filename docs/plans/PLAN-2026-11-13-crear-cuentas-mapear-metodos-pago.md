# PLAN-2026-11-13-crear-cuentas-mapear-metodos-pago (v1)

**Task:** TASK-crear-cuentas-mapear-metodos-pago · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-crear-cuentas-mapear-metodos-pago-pantalla-cuentas-metodos · ADR-crear-cuentas-mapear-metodos-pago-modulo-y-contrato

## Objective
Crear la base del módulo `accounting`: cuentas destino por empresa, mapeo método de pago → cuenta, pantalla de configuración y habilitación condicionada a un mapeo completo, sin alterar Ventas, Cobros ni reportes.

## Context
Ver TASK (hechos con `archivo:línea`) y ADR/DDR. Insumo: tarjeta Trello PB-ACC-001.

# Specification

## Domain context
`accounting` (nuevo). Relacionados solo por clave de módulo: `sales`, `receivables`. `modularity` consulta a `accounting.services` en la habilitación.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Cuenta destino | Lugar donde se recibe dinero (Caja, Banco…), con nombre, moneda y estado | Trello |
| Método de pago | Uno de `CASH, QR, BANK_TRANSFER, CARD, OTHER`, mismo código en Ventas y Cobros | `sales/domain/enums.py:35`, `receivables/domain/obligation.py:19` |
| Mapeo | Un método de la empresa → una cuenta vigente (más estado activo/inactivo del método) | Trello/ADR |
| Mapeo completo | Todo método activo tiene cuenta activa en BOB | Trello/ADR |

## Current behavior
Sin cuentas ni mapeo; el método de pago es solo texto en el pago (TASK).

## Expected behavior
La persona admin crea/edita/desactiva cuentas, asigna cuenta a cada método (varios métodos pueden compartir cuenta) y puede desactivar métodos. Habilitar `accounting` solo funciona con mapeo completo. Empresas aisladas entre sí. Con `accounting` deshabilitado nada cambia.

## Domain rules / invariants
- INV-01 Nombre de cuenta recortado, 1-80 caracteres, único por empresa sin distinguir mayúsculas.
- INV-02 Moneda de cuenta ∈ {BOB, USD}; solo `BOB` puede ser destino (moneda de los flujos).
- INV-03 Un método tiene como máximo una fila de mapeo por empresa (destino único vigente).
- INV-04 Destino debe ser cuenta de la misma empresa, activa y BOB.
- INV-05 No se desactiva ni se cambia a moneda incompatible una cuenta con métodos **activos** asignados (409 con lista de métodos).
- INV-06 Las cuentas no se eliminan (no hay endpoint de borrado).
- INV-07 Los 5 métodos nacen activos y sin cuenta; no se crean cuentas ni mapeos automáticos.
- INV-08 Habilitar `accounting` exige que todo método activo tenga cuenta válida; si no, 409 `incomplete_configuration` con los métodos faltantes. (Los flujos habilitados cubren los mismos 5 métodos, por lo que se exige para todos los activos; no se pide ningún flujo concreto.)
- INV-09 Deshabilitar `accounting` no borra configuración.

## Acceptance criteria
- AC-01 Empresa A configura Efectivo→Caja y Transferencia/QR→Banco; empresa B configura destinos propios sin verse entre sí.
- AC-02 Se rechaza cuenta de otra empresa (404), cuenta en moneda distinta de BOB y cuenta inactiva como destino (400).
- AC-03 Desactivar una cuenta con métodos activos asignados → 409 con los métodos; tras reasignarlos o desactivarlos, se permite.
- AC-04 Cambiar Transferencia de Banco A a Banco B actualiza el destino vigente; `resolve_account` devuelve Banco B desde entonces y el cambio no toca datos previos (no existen entradas aún; la cuenta se congelará por entrada en la historia siguiente).
- AC-05 Habilitar `accounting` con algún método activo sin cuenta → 409 con los métodos; con mapeo completo → habilitado. Ventas y Cobros se comportan igual con el módulo deshabilitado (por defecto).
- AC-06 Solo admin de empresa accede a la API y a la pantalla (403 resto).
- AC-07 La pantalla cubre cargando, vacío, error y éxito; crear, editar, activar/desactivar cuenta; asignar y desactivar método.
- AC-08 Correspondencia de códigos con Ventas y Cobros verificada por test.

## Edge cases / Error cases
- EDGE-01 Nombre duplicado → 400 por campo. EDGE-02 Cuenta inexistente/ajena en mapeo → 404. EDGE-03 Método desconocido → 404. EDGE-04 Desactivar método sin cuenta es válido. EDGE-05 Cuenta ya inactiva asignada a un método **inactivo**: permitido; al reactivar el método se revalida (400).
- EDGE-06 Dos peticiones concurrentes sobre el mismo método: `unique(company_id, method)` + `update_or_create` atómico.

## Authorization / permissions
`CompanyAdminPermission` por defecto; empresa siempre del usuario autenticado. Los endpoints de configuración no exigen `accounting` habilitado.

## API contract
- API-01 `GET/POST /api/accounting/accounts/` (filtro `?active=`), `GET/PATCH /api/accounting/accounts/<id>/`, `POST .../activate/` y `.../deactivate/`.
- API-02 `GET /api/accounting/payment-methods/` → 5 métodos `{code, label, is_active, account: {id,name,currency,is_active}|null}`.
- API-03 `PUT /api/accounting/payment-methods/<code>/` con `{account_id, is_active}`.
- API-04 `POST /api/modules/accounting/enable/` → 409 `{code:'incomplete_configuration', missing:[…métodos]}` si aplica. Contrato nuevo y aditivo; sin cambios a endpoints existentes.

## UI behavior
- UI-01 Ruta `/pocketbiz/accounting/settings`, menú Contabilidad → Configuración → Cuentas y Métodos de pago, solo admin.
- UI-02 Pestaña Cuentas: lista, estado badge, diálogo crear/editar, confirmación de desactivación con lista de métodos afectados.
- UI-03 Pestaña Métodos: 5 filas, `ng-select` de cuentas BOB activas, interruptor de activo.
- UI-04 Estados cargando/vacío/error/éxito; textos i18n es/en/pt (plantilla: configuración con listados en pestañas, design-system §5).
- UI-05 En Módulos, el 409 de habilitar muestra los métodos faltantes y enlace a la pantalla.

## Non-functional requirements
Dinero: no hay montos; el catálogo de moneda es texto controlado. Sin secretos. Migración solo aditiva.

## Out of scope
Libro de entradas, saldos, partida doble, fiscal, egresos (Compras/Gastos), transferencias, saldos iniciales, reversiones, multimoneda real, cambios en Ventas/Cobros/Reportes, bloqueo de cobros por método inactivo.

## Open questions
- Cuándo y cómo se aplica la regla «método inactivo no se puede usar al cobrar» (historia de entradas).

# Test Specification

## Unit tests
Dominio de cuenta y mapeo (INV-01..05, EDGE-05); test de correspondencia de métodos con `sales` y `receivables` (AC-08).

## Integration tests
API con dos empresas (AC-01, AC-02, AC-03, AC-04, AC-06), precondición de habilitación (AC-05), concurrencia del `PUT` (EDGE-06), gate en `test_enforcement.py` para `accounting`, test de fronteras (`modularity → accounting` solo por `services.py`). Frontend: specs de servicio, página (estados), diálogo, `provideTestTranslations()`; `npm run i18n:check`, lint y build.

## E2E
**NO** — flujo de configuración cubierto por integración API y specs de componentes; sin nueva dependencia.

## Regression tests
Suites de `modularity`, `sales`, `receivables` y `test_enforcement` siguen verdes.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | Integración API dos empresas |
| AC-02 | Dominio + integración API |
| AC-03 | Dominio + integración API |
| AC-04 | Integración API (`resolve_account` antes/después) |
| AC-05 | Integración `modularity` + regresión Ventas/Cobros |
| AC-06 | Integración API (no admin / sin empresa) |
| AC-07 | Specs de componentes frontend + i18n:check |
| AC-08 | Unit test de correspondencia |

# Implementation Plan

## Architecture considerations
Ver ADR: puerto de precondición en `EnableModule`; fachada `accounting/services.py`; sin importar `modularity` desde dominio.

## Proposed solution
Módulo `accounting` DDD pragmático (dominio puro, casos de uso, repositorios `Django…Repository(company_id)`, vistas DRF) + precondición en `modularity` + pantalla Angular bajo `features/accounting`.

## Files/components affected
- Backend: `modules/accounting/**` (nuevo), `config/settings/base.py`, `config/urls.py`, `modularity/domain/modules.py` (clave `accounting`), `modularity/application/use_cases.py` y `api/views.py` (precondición, 409), adaptador en `modularity/infrastructure`, `modularity/tests/test_enforcement.py`, tests de fronteras.
- Migraciones: `accounting/0001_initial` (nueva).
- Frontend: `features/accounting/**`, `app.routes.ts`, `assets/data/routes.json`, `assets/i18n/{es,en,pt}.json`, manejo del 409 en `features/settings`.
- Docs: `docs/architecture/ddd.md` (nota y dependencia), `docs/design/design-system.md` §6 (menú), `docs/producto/modulos-implementados.md`.

## Implementation steps
1. Dominio y tests (INV-01..05, 07).
2. Modelos, migración 0001, repositorios.
3. Casos de uso + API + fachada (AC-01..04, 06, API-01..03).
4. Clave `accounting` en el catálogo y precondición de habilitación (INV-08, AC-05, API-04); gate y fronteras.
5. Servicio y pantalla Angular + i18n (UI-01..05).
6. Docs y verificación completa.

## Database / migrations
Solo `CreateModel`; nunca se editan migraciones aplicadas.

## Risks
Ciclo de módulos (mitigado); catálogo de métodos duplicado (test AC-08).

## New dependencies
Ninguna.
