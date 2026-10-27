# PLAN-2026-10-27-habilitar-modulos-por-empresa (v1)

**Task:** TASK-habilitar-modulos-por-empresa · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-habilitar-modulos-por-empresa-pantalla-modulos · ADR-habilitar-modulos-por-empresa-modelo-y-contrato

## Objective
Que cada empresa elija qué módulos usa: pantalla `/settings/modules` (solo admin), reglas de dependencias en backend y menú/rutas filtrados por la selección de la empresa.

## Context
Ver TASK. Decisiones del usuario: mapa de dependencias de la propuesta, Compras/Inventario habilitables con placeholder, defaults = 5 módulos actuales, sin bloqueo 403 en API de negocio (PB-MOD-004).

# Specification

## Domain context
Bounded context ligero **Modularity** (configuración de la empresa). Relacionados solo por clave de módulo: catalog, customers, sales, expenses, reporting (existentes), purchases, inventory (futuros). No importa ningún módulo de negocio ni `accounts`.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Módulo | Capacidad de negocio del producto con clave estable | Historia PB-MOD-001 |
| Módulo base | Siempre habilitado, sin interruptor: Acceso/Empresa y Catálogo | Historia |
| Dependencia obligatoria (`requires`) | Módulos que deben estar habilitados para habilitar este | Historia |
| Integración opcional (`optional`) | Módulos con los que puede integrarse si están habilitados; no bloquea | Historia |
| Habilitado | Estado de un módulo para una empresa | Historia |

## Current behavior
Todos los módulos disponibles siempre para todas las empresas (`routes.json` estático, `sidebar.service.ts:17`).

## Expected behavior
- Cada empresa tiene su propio conjunto de módulos habilitados. Valores por defecto en el primer acceso: Catálogo y Acceso (base) + Clientes, Ventas, Gastos, Reportes. Compras e Inventario deshabilitados.
- `/settings/modules` lista los 8 módulos con estado, dependencias obligatorias, integraciones opcionales y acción. Habilitar/Deshabilitar abre un diálogo de resumen y confirma.
- El menú lateral y las rutas solo muestran módulos habilitados de la empresa del usuario; al recargar se refleja el estado guardado.

## Domain rules / invariants
- INV-01 (nueva): Acceso/Empresa y Catálogo siempre están habilitados y no se pueden deshabilitar.
- INV-02: Habilitar un módulo exige que todas sus `requires` estén habilitadas; si no, se rechaza e informa los nombres faltantes.
- INV-03: No se puede deshabilitar un módulo requerido por otro módulo habilitado; se informan los dependientes.
- INV-04: La selección es por `company_id`; habilitar en una empresa no cambia otra.
- INV-05: Habilitar/deshabilitar no instala código ni ejecuta migraciones por empresa.
- INV-06: Mapa: sales→{catalog} (opc. customers); customers→∅; expenses→∅; reporting→{sales, expenses} (opc. customers); purchases→{catalog, expenses}; inventory→{catalog} (opc. sales, purchases).

## Acceptance criteria
- AC-01: Dos empresas conservan selecciones independientes (habilitar Inventario en A no lo habilita en B).
- AC-02: Acceso/Empresa y Catálogo figuran como base, sin interruptor editable (UI) y el backend rechaza deshabilitarlos.
- AC-03: Habilitar un módulo con dependencias faltantes falla con los nombres de las faltantes; la UI los muestra y bloquea la acción.
- AC-04: Habilitar Inventario (con Catálogo base) y recargar muestra su menú solo en esa empresa.
- AC-05: Deshabilitar un módulo no requerido por otros habilitados lo quita del menú tras recargar; si lo requieren otros, se bloquea mostrando cuáles.
- AC-06: Solo el admin de una empresa activa accede a la API y a `/settings/modules`.
- AC-07: El diálogo de confirmación resume módulo, empresa y dependencias afectadas antes de confirmar.
- AC-08: Defaults: una empresa nueva o existente, al primer acceso, tiene Clientes, Ventas, Gastos y Reportes habilitados; el menú actual no cambia para ellas.
- AC-09: Sin migraciones de datos ni de esquema por empresa; la migración solo crea las tablas nuevas.

## Edge cases / Error cases
- EDGE-01: Clave de módulo desconocida → 404.
- EDGE-02: Habilitar ya habilitado / deshabilitar ya deshabilitado → 200 idempotente.
- EDGE-03: Dos primeras lecturas simultáneas de la misma empresa → sin duplicados ni error 500.
- EDGE-04: Reportes deshabilitado → Dashboard oculto; entrar por URL a un módulo deshabilitado redirige a la primera ruta visible.
- EDGE-05: Falla la carga de módulos en el frontend → se muestran solo los ítems base y un error recuperable; no se desloguea.
- EDGE-06: Usuario sin empresa o empresa inactiva → 403.

## Authorization / permissions
`CompanyAdminPermission` (por defecto) en todas las vistas; empresa de `company_id_from(request)`.

## API contract
- API-01: `GET /api/modules/` → lista (`key,name,description,is_base,enabled,requires[],optional[],missing_requires[]`).
- API-02: `POST /api/modules/<key>/enable/` → 200 módulo; 404; 409 `{detail, missing:[nombres]}`.
- API-03: `POST /api/modules/<key>/disable/` → 200; 400 base; 404; 409 `{detail, dependents:[nombres]}`.
- Compatibilidad: endpoints nuevos; no cambia ningún contrato existente.

## UI behavior
- UI-01: Ítem de menú «Configuración › Módulos» (`/settings/modules`) y filtrado del menú por módulo (DDR; design-system §6).
- UI-02: Lista según DDR (design-system §5 «Lista» con tabla simple), con estados cargando/error/éxito.
- UI-03: Diálogo de confirmación según DDR.
- UI-04: Placeholder «Próximamente» en `/purchases` y `/inventory`.

## Non-functional requirements
Textos en español; accesibilidad del design-system §7; sin dependencias nuevas.

## Out of scope
Bloqueo 403 en la API de negocio por módulo, validación de datos al deshabilitar (PB-MOD-004), roles distintos de admin, construir Compras e Inventario, auditoría de cambios.

## Open questions
Ninguna bloqueante.

# Test Specification

## Unit tests
- Dominio (`modularity/tests/test_domain.py`): catálogo coherente (claves únicas, `requires`/`optional` existen, sin ciclos, base sin dependencias); reglas INV-01..03, EDGE-02.
## Integration tests
- API (`test_api.py`): GET, enable, disable, 404, 409 con nombres, 400 base, 403 usuario sin empresa/empresa inactiva, aislamiento entre dos empresas, defaults y EDGE-03 (doble sembrado).
- Repositorio: filtra por `company_id`; `accounts/test_guards.py` debe seguir en verde (incluir el nuevo repositorio si el guard lo recorre).
- Frontend (Karma): `ModulesService`, filtrado del menú (`sidebar-menu.spec.ts` actualizado), `moduleGuard`, `ModuleListComponent` (estados, bloqueo con dependencias faltantes, base sin botón), diálogo.
## E2E
NO — flujo cubierto con integración y pruebas de componentes; no se instala Playwright. Verificación manual en publish: habilitar Inventario con dos empresas y recargar.
## Regression tests
`python manage.py test` completo y `npm test`, `npm run lint`, `npm run build`.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | test_api aislamiento entre empresas |
| AC-02 | test_domain (INV-01), test_api 400, spec del componente (sin botón) |
| AC-03 | test_domain + test_api 409 con nombres; spec componente (mensaje y botón deshabilitado) |
| AC-04 | test_api enable inventory; spec sidebar/servicio de módulos (ítem visible); verificación manual |
| AC-05 | test_api disable + 409 dependents; spec de filtrado del menú |
| AC-06 | test_api 403 sin empresa/inactiva; spec del guard no sustituye la API |
| AC-07 | spec del diálogo |
| AC-08 | test_api defaults (empresa nueva y empresa preexistente sin filas) |
| AC-09 | revisión de la migración (solo `CreateModel`) + test de que no hay `RunPython` |

# Implementation Plan

## Architecture considerations
ADR: app `modularity` independiente, catálogo en código, filas por empresa sin FK, sembrado en primera lectura, frontend consulta la API al cargar.

## Proposed solution
Dominio puro (`ModuleDefinition`, `MODULE_CATALOG`, funciones `can_enable`, `can_disable`) + casos de uso (`ListModules`, `EnableModule`, `DisableModule`) sobre un repositorio `DjangoCompanyModuleRepository(company_id)`; vistas DRF finas; en Angular `features/settings/` (página, diálogo, servicio API) + `core/service/modules.service.ts` y `moduleGuard`.

## Files/components affected
- Backend: `modules/modularity/{__init__,apps,models}.py`, `domain/`, `application/`, `infrastructure/django/{models,repositories}.py`, `api/{urls,views,serializers}.py`, `migrations/0001_initial.py`, `tests/`; `config/settings/base.py` (INSTALLED_APPS), `config/urls.py` (`api/modules/`); extender `modules/sales/tests/test_boundaries.py` o equivalente para que los módulos de negocio no importen `modularity`.
- Frontend: `app/features/settings/` (pages/module-list, components/module-confirm-dialog, services, models), `app/core/service/modules.service.ts`, `app/core/guard/module.guard.ts`, `layout/sidebar/sidebar.component.ts` y `sidebar.metadata.ts` (campo `module`), `assets/data/routes.json` (campo `module`, Configuración, Compras, Inventario), `assets/i18n/{es,en,de}.json`, `app.routes.ts` (`data.module` y rutas `settings/modules`, `purchases`, `inventory`), `sidebar-menu.spec.ts`.
- Docs: `docs/architecture/ddd.md` (sección de módulos y mapa), `docs/design/design-system.md` §6, `docs/producto/modulos-implementados.md`.

## Implementation steps
1. Dominio y catálogo + pruebas unitarias (INV-01..03, INV-06).
2. Modelo, migración (solo `CreateModel`), repositorio con sembrado idempotente (AC-08, AC-09, EDGE-03).
3. Casos de uso y API (API-01..03, AC-01..06, EDGE-01/02/06).
4. Frontend: modelos, `ModulesService` (carga y refresco), `moduleGuard`, filtrado del menú y rutas (AC-04, AC-05, EDGE-04/05).
5. Pantalla `/settings/modules` y diálogo (UI-02, UI-03, AC-02, AC-03, AC-07).
6. Placeholder de Compras e Inventario, ítem Configuración, i18n (UI-01, UI-04).
7. Actualizar documentación y pasar suites completas.

## Database / migrations
Una migración nueva `modularity/0001_initial` con dos `CreateModel` y la restricción única; sin `RunPython`. No se edita ninguna migración existente.

## Risks
- La API de negocio sigue accesible aunque el módulo esté oculto (aceptado hasta PB-MOD-004).
- Redirección post-login si Reportes está deshabilitado (EDGE-04). Decisión (REV-03): el destino post-login y los enlaces de inicio siguen en `/dashboard/main`; `moduleGuard` redirige a `/catalog/products` cuando Reportes está deshabilitado. Es el comportamiento intencional; no se duplica la lógica de módulos en el login.
- Menú dependiente de una llamada de red: manejo de error EDGE-05.

## New dependencies
Ninguna.
