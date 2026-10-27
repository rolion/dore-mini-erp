# PLAN-2026-10-27-bloquear-api-modulos-deshabilitados (v1)

**Task:** TASK-bloquear-api-modulos-deshabilitados · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-bloquear-api-modulos-deshabilitados-pantalla-no-habilitado · ADR-bloquear-api-modulos-deshabilitados-permiso-por-modulo

## Objective
Que la API de negocio rechace con 403 toda consulta o escritura de un módulo deshabilitado para la empresa del usuario, que Ventas y Reportes sigan funcionando sin Clientes, y que Angular muestre «Módulo no habilitado» en vez de una tabla vacía.

## Context
Depende de PB-MOD-001 (PR #15, sin mergear: este PR se apila sobre su rama). Ver TASK.

# Specification

## Domain context
Contexto `modularity` (configuración) como fuente; los contextos de negocio catalog, customers, sales, expenses y reporting solo declaran qué módulo son. Reporting y Sales usan Customers como integración opcional.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Módulo habilitado | Clave en `effective_enabled` de la empresa (base + elegidos) | `modularity/domain/modules.py` |
| `required_modules` | Tupla de claves que una vista exige habilitadas | ADR |
| Integración opcional | Dato de otro módulo que enriquece un flujo y puede faltar | PB-MOD-001 |

## Current behavior
Ver TASK: ninguna vista de negocio comprueba el módulo (`backend/config/settings/base.py:87-89`); `error.interceptor.ts:15-21` solo trata 401; `module.guard.ts` redirige en silencio.

## Expected behavior
Con un módulo deshabilitado, todas las rutas de su API responden 403 `module_disabled`; con Clientes deshabilitado, Ventas y Reportes siguen respondiendo sin integración; Angular lleva a «Módulo no habilitado».

## Domain rules / invariants
- INV-01 (nueva): la decisión de acceso depende de la empresa del usuario autenticado, nunca de datos del cliente (`shared/tenancy.py`).
- INV-02 (nueva): una vista sin `required_modules` se rechaza (fail-closed).
- INV-03 (existente): los módulos base (`access`, `catalog`) siempre están habilitados.
- INV-04 (existente): Reportes exige Ventas y Gastos habilitados (dependencias de PB-MOD-001).

## Acceptance criteria
- AC-01: GET/POST/PATCH/PUT/DELETE y acciones de cualquier ruta de un módulo deshabilitado responden 403 con `{detail, code: 'module_disabled', module}`; no se lee ni modifica ningún dato.
- AC-02: con el módulo habilitado el comportamiento y los códigos de respuesta actuales no cambian (regresión completa).
- AC-03: la empresa sale de la sesión; un `company_id` enviado en query o cuerpo se ignora y la configuración de otra empresa no afecta.
- AC-04: un cambio de módulos (enable/disable) rige desde la petición siguiente, sin reiniciar ni cerrar sesión.
- AC-05: sin sesión → 401; usuario sin empresa o empresa inactiva → 403 con los mensajes actuales; solo después se evalúa el módulo.
- AC-06: Catálogo (base) responde siempre; `modularity` no se bloquea a sí mismo.
- AC-07: con Clientes deshabilitado, Ventas crea y lista pedidos sin cliente; asignar o filtrar por `customer_id` responde 400 `{customer_id: ['El módulo Clientes no está habilitado.']}`; los pedidos con cliente guardado salen con `customer: null`.
- AC-08: con Clientes deshabilitado, los reportes dashboard, ventas, gastos, canal y top de productos responden 200; `pending` devuelve `customer: null`; `reports/top-customers/` responde 403 `module_disabled` con `module: 'customers'`.
- AC-09: una guarda automática falla si una ruta `api/` no pública no declara `required_modules`, si usa una clave inexistente o si una vista de negocio sobrescribe el permiso por defecto.
- AC-10: Angular, ante un 403 `module_disabled` o al abrir la URL de un módulo deshabilitado, muestra «Módulo no habilitado» con «Volver al inicio» (a una pantalla válida), actualiza el menú y no deja una lista vacía como resultado válido.
- AC-11: al deshabilitar un módulo sus datos no se tocan; al habilitarlo de nuevo vuelven a verse.
- AC-12: sin sesión, la URL de un módulo lleva al login existente.

## Edge cases / Error cases
- EDGE-01: empresa sin configuración inicializada → se siembran los valores por defecto y se evalúa.
- EDGE-02: ruta con dos módulos (`top-customers`) → rechaza con el primero que falte.
- EDGE-03: dos pestañas, una deshabilita y otra opera → la petición siguiente de la otra recibe 403 y su menú se actualiza.
- EDGE-04: clave inexistente en `required_modules` → error de configuración detectado por la guarda (nunca en producción).
- EDGE-05: el proveedor de `module_gate` no está registrado → `ImproperlyConfigured`, no se concede acceso.

## Authorization / permissions
Solo el rol admin existe; el orden de evaluación es autenticación → empresa activa → rol → módulo.

## API contract
- API-01: respuesta de rechazo 403 `{ "detail": "Módulo no habilitado", "code": "module_disabled", "module": "<key>" }`. Compatible hacia atrás: los clientes actuales ya manejan 403.
- API-02: tabla de rutas → módulo: `products` → `catalog`; `customers` → `customers`; `orders` → `sales`; `expenses` y `expense-categories` → `expenses`; `reports/*` → `reporting` (más `customers` en `top-customers`); `modules` → `()`.
- API-03: `customer` pasa a `null` en pedidos y pendientes con Clientes deshabilitado; el filtro/asignación por cliente responde 400.

## UI behavior
- UI-01: ruta `/module-disabled` (query `module` opcional) con la pantalla simple del DDR (`design-system.md` §5, patrón `coming-soon`).
- UI-02: `moduleGuard` navega a `/module-disabled` en lugar de redirigir en silencio.
- UI-03: `errorInterceptor` trata el 403 `module_disabled`: recarga módulos, navega a la pantalla y propaga el error.
- UI-04: «Volver al inicio» → `/dashboard/main` si Reportes está habilitado; si no, `/catalog/products`.

## Non-functional requirements
Una consulta de módulos por petición como máximo (caché por petición); sin dependencias nuevas; sin migración.

## Out of scope
Desactivación segura / validar datos (PB-MOD-004), pantallas de configuración por módulo (PB-CFG-001), otros roles, ocultar tarjetas/campos por módulo (PB-MOD-003).

## Open questions
Ninguna que bloquee.

# Test Specification

## Unit tests
- `shared/module_gate`: sin proveedor lanza error; con proveedor delega.
- `CompanyModulePermission`: sin atributo → deniega; `()` → permite; clave deshabilitada → `ModuleDisabled`.

## Integration tests
- API por módulo con una tabla de rutas (todas las vistas × métodos): módulo apagado → 403 `module_disabled`; encendido → códigos actuales.
- Aislamiento: dos empresas con configuraciones distintas; `company_id` enviado se ignora.
- Cambio de configuración entre dos peticiones.
- Ventas y Reportes con Clientes apagado (AC-07, AC-08).
- Frontend: specs del interceptor (403 `module_disabled`), guard, y componente `module-disabled`.

## E2E
**NO** — los flujos se cubren con integración de API y specs de Angular; no hay dependencia E2E instalada.

## Regression tests
Suite completa del backend (`manage.py test`) y Karma de core/settings/sidebar.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01, AC-06 | Integración API: tabla de rutas × métodos |
| AC-02 | Suite completa existente |
| AC-03 | Integración: dos empresas y `company_id` en query/cuerpo |
| AC-04 | Integración: enable/disable entre peticiones |
| AC-05 | Integración: 401/403 actuales antes del módulo |
| AC-07, AC-08 | Integración Sales/Reporting con Clientes apagado |
| AC-09 | `test_guards.py` ampliado |
| AC-10, AC-12 | Specs de interceptor, guard y componente |
| AC-11 | Integración: deshabilitar, habilitar y releer datos |

# Implementation Plan

## Architecture considerations
Ver ADR: `shared/module_gate.py` como puerto; permiso central en `config/permissions.py`; sin importar `modularity` desde negocio.

## Proposed solution
Permiso por defecto `CompanyModulePermission` + `required_modules` por vista + excepción `ModuleDisabled`; adaptadores de integración que consultan el puerto; interceptor, guard y pantalla en Angular.

## Files/components affected
- Backend: `shared/module_gate.py` (nuevo), `config/permissions.py` (nuevo), `config/settings/base.py`, `modularity/apps.py` (registro del proveedor) y su excepción `ModuleDisabled`, `required_modules` en todas las vistas de catalog, customers, sales, expenses, reporting y modularity, `sales/infrastructure/adapters.py`, `sales/application/commands.py`, `sales/api/filters.py` y serializers de pedidos, `reporting/infrastructure/adapters.py` y serializers, `accounts/test_guards.py`.
- Frontend: `features/settings/pages/module-disabled/` (nuevo), `app.routes.ts`, `core/guard/module.guard.ts`, `core/interceptor/error.interceptor.ts`, `core/service/modules.service.ts` (si hace falta), specs.
- Docs: `design-system.md` §6, `modulos-implementados.md` (§3.7).
- Migraciones: ninguna.

## Implementation steps
1. `shared/module_gate.py` + registro en `modularity` (INV-01, EDGE-05).
2. `CompanyModulePermission`, `ModuleDisabled` y ajuste de `DEFAULT_PERMISSION_CLASSES` (AC-01, AC-05, INV-02).
3. `required_modules` en todas las vistas según API-02 (AC-01, AC-06).
4. Ampliar `test_guards.py` (AC-09).
5. Integración opcional con Clientes en Sales y Reporting (AC-07, AC-08).
6. Tests de integración backend (AC-01..08, AC-11).
7. Frontend: pantalla, guard, interceptor y specs (AC-10, AC-12, UI-01..04).
8. Docs vivos y verificación (lint, build, Karma, suite backend).

## Database / migrations
Ninguna.

## Risks
- Una vista nueva sin declarar módulo queda rechazada (fail-closed) y la guarda lo avisa.
- Consultas extra por petición (caché por petición).
- Los datos de otra empresa nunca se mezclan: se mantiene `company_id_from`.

## New dependencies
Ninguna.
