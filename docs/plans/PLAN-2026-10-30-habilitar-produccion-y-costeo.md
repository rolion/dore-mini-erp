# PLAN-2026-10-30-habilitar-produccion-y-costeo (v1)

**Task:** TASK-habilitar-produccion-y-costeo · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-habilitar-produccion-y-costeo-modulos-y-bloqueos · ADR-habilitar-produccion-y-costeo-capacidades-y-bloqueos

## Objective
Que cada empresa pueda habilitar Producción y Costeo desde Configuración → Módulos con sus dependencias (módulos y capacidad de valoración), con bloqueos de desactivación explicados y una fecha de adopción de Costeo, sin afectar a las empresas que no los usan.

## Context
Ver TASK. Ni Producción, Costeo ni la valoración de Inventario existen; esta historia entrega catálogo, reglas, puerto de extensión, contrato API, menú y pantallas de módulo. Supuestos S-1…S-5 del TASK.

# Specification

## Domain context
Bounded context ligero **Modularity**. Relacionados solo por clave/puerto: `inventory` (capacidad futura), `production`, `costing` (futuros). `modularity` no importa módulos de negocio.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Producción | Módulo para recetas, elaboraciones y envasados | Historia |
| Costeo | Módulo de costos por lote y análisis | Historia |
| Capacidad | Funcionalidad que ofrece un módulo y que otro exige sin ser un módulo (p. ej. valoración de Inventario) | Historia / S-1 |
| Bloqueo de desactivación | Dato abierto (órdenes abiertas, costos sin cerrar) que impide deshabilitar un módulo | Historia |
| Fecha de adopción | Momento en que se habilita Costeo; los lotes anteriores no se recalculan | Historia / S-4 |

## Current behavior
Ver TASK «Hechos encontrados»: 6 módulos no base; solo `requires`; 409 con `missing`/`dependents`; deshabilitar con aviso genérico.

## Expected behavior
- El catálogo incluye `production` y `costing`, deshabilitados por defecto. La librería (sin ellos) no cambia; Dore puede habilitar Producción sin Costeo, sin Compras.
- Habilitar informa lo que falta: módulos y/o capacidades. Costeo exige Producción habilitado y la capacidad `inventory.valuation` disponible.
- Deshabilitar informa dependientes y bloqueos con cómo resolverlos; no cambia otros módulos ni borra datos de negocio.
- Costeo registra su fecha de adopción al habilitarse y dispara el gancho de valoración de existencias actuales; no recalcula lotes anteriores.

## Domain rules / invariants
- INV-01 (existente, ampliada): habilitar exige todos los `requires` (Producción: catalog, inventory; Costeo: production).
- INV-02 (nueva): habilitar exige las capacidades requeridas disponibles para la empresa; sin proveedor registrado, no disponible.
- INV-03 (existente): no se deshabilita un módulo requerido por otro habilitado (Inventario ← Producción; Producción ← Costeo).
- INV-04 (nueva): no se deshabilita un módulo con bloqueos de datos informados por sus guardas.
- INV-05 (nueva): la fecha de adopción es la fecha de habilitación; una rehabilitación fija una nueva; nunca se recalculan lotes anteriores.
- INV-06 (nueva): si un gancho de habilitación falla, el módulo no queda habilitado.
- INV-07: Compras no es obligatoria para Producción.
- INV-08 (existente): todo por `company_id` de la sesión.

## Acceptance criteria
- AC-01 Sin habilitar Producción/Costeo, la empresa opera igual (defaults sin cambio); Producción se habilita sin Costeo si Catálogo e Inventario están habilitados, sin requerir Compras.
- AC-02 Habilitar Producción sin Inventario → 409 con «Inventario» faltante; Costeo sin Producción → 409 con «Producción»; Costeo sin valoración → 409 con la capacidad «Valoración de Inventario» faltante y no se habilita.
- AC-03 La API de módulos de Producción/Costeo responde 403 `module_disabled` si el módulo está deshabilitado; el menú solo muestra los grupos de módulos habilitados; sin valoración no hay costos (Costeo no habilitable y `capability_available` informa el estado).
- AC-04 Deshabilitar Inventario con Producción activo → 409 `dependents`; Producción con Costeo activo → 409 `dependents`; Producción u otro módulo con bloqueos de datos → 409 `blockers` con mensaje y resolución. No se deshabilita ningún otro módulo ni se borran datos.
- AC-05 Habilitar Costeo con la capacidad disponible fija `adopted_at`, invoca el gancho con empresa y fecha una sola vez y no calcula nada retroactivo; la lista muestra la fecha.
- AC-06 La pantalla de módulos muestra capacidades, dependencias faltantes, fecha de adopción y los motivos de bloqueo con cómo resolver; el menú agrega Producción y Costeo con sus ítems.

## Edge cases / Error cases
- EDGE-01 Habilitar/deshabilitar repetido es idempotente (sin segundo gancho ni consulta de guardas).
- EDGE-02 Gancho que falla → 5xx controlado y estado sin cambios (transacción).
- EDGE-03 Capacidad disponible para una empresa y no para otra (aislamiento).
- EDGE-04 Costeo habilitado y la capacidad deja de estar disponible: la lista lo marca (`missing_capabilities`) y el módulo no debe mostrar costos.
- EDGE-05 Dependientes y bloqueos a la vez: ambos en el mismo 409.
- EDGE-06 Rehabilitar Costeo → fecha de adopción nueva; historial conserva los cambios.
- EDGE-07 Clave desconocida 404; módulo base 400 (sin cambios).

## Authorization / permissions
Solo admin de empresa activa (permiso por defecto). Las vistas de módulos nuevos declararán `required_modules` con su clave.

## API contract
- API-01 `GET /api/modules/` agrega por módulo: `capabilities`, `missing_capabilities`, `adopted_at`, `disable_blockers` (aditivo).
- API-02 `POST /api/modules/<key>/enable/` → 200 módulo; 409 `{detail, missing}` o `{detail, missing_capabilities}`.
- API-03 `POST /api/modules/<key>/disable/` → 200; 409 `{detail, dependents?, blockers?}`.
- Retrocompatible: campos existentes sin cambios.

## UI behavior
- UI-01 Lista de módulos: según DDR (capacidades en «Requiere», motivos visibles, fecha de adopción).
- UI-02 Diálogo: filas condicionales de adopción y aviso; 409 mostrado con los mensajes del servidor.
- UI-03 Menú: grupos Producción y Costeo, i18n es/en/de.
- UI-04 Pantallas destino: placeholders `ComingSoon`; Configuración con `module-settings` (sin ajustes, con historial).

## Non-functional requirements
Sin consultas adicionales significativas: una consulta de guardas por módulo habilitado; capacidades por llamada a proveedor. Sin dependencias nuevas.

## Out of scope
Implementar Producción, Costeo, valoración de Inventario (PB-VAL-001/002), las guardas concretas de órdenes/costos, el cálculo de costos y la desactivación segura completa (PB-MOD-004).

## Open questions
- Ninguna que bloquee. A confirmar por producto cuando existan PB-VAL: quién registra la capacidad y si depende de configuración por empresa (el contrato ya recibe `company_id`).

# Test Specification

## Unit tests
- Dominio: catálogo (claves, `requires`, defaults, Compras opcional), `check_can_enable` con capacidades, reglas de bloqueo (INV-01…05).
- Casos de uso con puerto falso: habilitar con/sin capacidad, adopción, gancho único y rollback, deshabilitar con dependientes y bloqueos, idempotencia.

## Integration tests (API, `DJANGO_SETTINGS_MODULE=config.settings.test`)
- Contrato de GET/enable/disable (campos nuevos, 409 con `missing_capabilities`, `dependents`, `blockers`), aislamiento por empresa, historial, 403 `module_disabled` con una vista de prueba de `production`, y que la configuración de `production`/`costing` responde sin ajustes.
- `test_guards.py` y `test_boundaries.py` siguen verdes (`modularity` solo importa `shared`).

## Frontend (Karma)
- `module-list`: capacidades, motivo de bloqueo, adopción, botón deshabilitado; `module-confirm-dialog`: filas condicionales y 409; `modules.service`/modelo: mapeo de campos nuevos; sidebar: grupos visibles solo con módulo habilitado.

## E2E
**NO** — los flujos se cubren con API y componentes; no hay flujo crítico de punta a punta nuevo.

## Regression tests
Suite existente de `modularity`, `accounts/test_guards.py`, enforcement y specs de `settings`/sidebar.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | Unit dominio (defaults, Compras opcional) + API: habilitar Producción sin Compras con Inventario habilitado |
| AC-02 | API/casos de uso: 409 `missing` y `missing_capabilities` por cada combinación |
| AC-03 | API: vista de prueba con `required_modules=('production',)` 403/200; spec de sidebar; test de `capability_available` |
| AC-04 | API: 409 `dependents` (Inventario, Producción) y `blockers` con guarda falsa; verifica que no cambian otros módulos |
| AC-05 | Caso de uso/API: `adopted_at`, gancho una vez con empresa y fecha, rollback si falla, rehabilitación |
| AC-06 | Specs de `module-list`, diálogo y menú; revisión visual en `delivery-publish` |

# Implementation Plan

## Architecture considerations
Ver ADR: `shared/module_extensions.py` como puerto neutro; `modularity` lo usa por un puerto del caso de uso; sin importar negocio.

## Proposed solution
Ampliar `ModuleDefinition` y el catálogo; excepciones/chequeos de dominio; `ModuleExtensions` (puerto) con adaptador Django sobre `shared`; casos de uso y serializer ampliados; frontend con modelo, lista, diálogo, menú, rutas e i18n.

## Files/components affected
- Backend: `shared/module_extensions.py` (nuevo), `modularity/domain/modules.py`, `application/use_cases.py`, `api/views.py`, `api/serializers.py`, `infrastructure/django/` (adaptador), `modularity/tests/`.
- Frontend: `core/models/module.ts`, `features/settings/pages/module-list/*`, `components/module-confirm-dialog/*`, `core/service/modules.service.ts` (errores 409 ampliados), `assets/data/routes.json`, `assets/i18n/{es,en,de}.json`, `app.routes.ts` y specs.
- Docs: `docs/architecture/ddd.md` (nota), `docs/producto/modulos-implementados.md`, `docs/design/design-system.md` §6.

## Implementation steps
1. Dominio: campos `requires_capabilities`/`records_adoption`, entradas `production`/`costing`, catálogo de capacidades, errores y chequeos (INV-01…05).
2. `shared/module_extensions.py` + adaptador de `modularity` (puerto) con pruebas unitarias.
3. Casos de uso: habilitar (capacidades, adopción, gancho dentro de la transacción) y deshabilitar (dependientes + bloqueos) (AC-02, AC-04, AC-05).
4. Serializer y vistas: campos nuevos y 409 ampliados (API-01…03).
5. Pruebas API: AC-01…05, aislamiento, 403 de módulo deshabilitado, configuración sin ajustes.
6. Frontend: modelo y servicio, lista y diálogo (AC-06), menú, rutas, i18n.
7. Specs de frontend y documentación.

## Database / migrations
Sin migraciones (la adopción usa `enabled_at`; no hay tablas nuevas).

## Risks
- Carrera orden-vs-desactivación pendiente de la guarda definitiva en Producción (documentado).
- Costeo no habilitable hasta PB-VAL (esperado; se prueba con proveedores falsos).

## New dependencies
Ninguna.
