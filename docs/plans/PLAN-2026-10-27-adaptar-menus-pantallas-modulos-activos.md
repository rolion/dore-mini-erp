# PLAN-2026-10-27-adaptar-menus-pantallas-modulos-activos (v1)

**Task:** TASK-adaptar-menus-pantallas-modulos-activos · **Modo:** COMPACTO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-adaptar-menus-pantallas-modulos-activos-inicio-y-menu · ADR: ninguno (ver ADR de PB-MOD-001 y PB-MOD-002)

## Objective
Que el menú, la página inicial y los controles opcionales se adapten a los módulos activos de la empresa, sin pantallas de error innecesarias, y dejar un mecanismo reutilizable (`*appIfModule`) para los campos de Inventario.

# Specification
- **Expected behavior:** el menú muestra solo grupos con hijos habilitados; con Reportes apagado el inicio es Catálogo sin mensaje de error; los controles que dependen de un módulo opcional aparecen solo si ese módulo está activo.
- **Acceptance criteria:**
  - AC-01: un ítem con `module` se oculta si su módulo está deshabilitado; los hijos de un grupo se filtran por su módulo (heredado del grupo si no declaran uno) y un grupo sin hijos visibles no se muestra; los grupos sin módulo (Configuración) siguen visibles.
  - AC-02: con Reportes habilitado, `/pocketbiz/dashboard/main` muestra el dashboard; con Reportes deshabilitado, esa ruta redirige a `/pocketbiz/catalog/products` sin pasar por «Módulo no habilitado» (login, registro, logo e iconos de inicio quedan en una pantalla válida).
  - AC-03: cualquier otra URL de un módulo deshabilitado sigue llevando a «Módulo no habilitado» con «Volver al inicio» a una pantalla válida (sin regresión de PB-MOD-002).
  - AC-04: `*appIfModule="'<clave>'"` renderiza su contenido solo cuando el módulo está habilitado y lo quita si se deshabilita; mientras no se conocen los módulos no renderiza.
  - AC-05: los controles de Clientes en pedidos y Reportes usan `*appIfModule` (sin cambio de comportamiento respecto a PB-MOD-002).
  - AC-06: con Inventario deshabilitado, Ventas, Pedidos y Reportes funcionan igual que hoy y no muestran errores por módulos ausentes (sin campos de almacén ni stock, que aún no existen).
  - AC-07: el panel de usuario sigue mostrando el nombre de la persona y de la empresa, y el ítem activo del menú queda resaltado (sin regresión).
- **Edge/error cases:** módulos aún sin cargar (menú solo con ítems sin módulo; guard espera la carga); error de carga (solo base); una empresa sin módulos opcionales (solo Catálogo y Configuración).
- **Out of scope:** campos reales de Inventario/Compras, configuración por módulo (PB-CFG-001), desactivación segura de datos (PB-MOD-004), cambios de API o permisos.

# Test Specification
| AC | Verificación |
|---|---|
| AC-01 | Specs de `SidebarComponent` (filtro de hijos y de grupos vacíos) y de `routes.json` |
| AC-02 | Spec de `moduleGuard` (ruta con `data.home`): redirige a Catálogo con Reportes apagado y deja pasar con Reportes habilitado |
| AC-03 | Specs existentes de `moduleGuard` y `ModuleDisabledComponent` |
| AC-04 | Spec de la directiva `IfModuleDirective` (habilitado, deshabilitado, sin cargar, cambio) |
| AC-05, AC-06 | Specs de lista y formulario de pedidos y de Reportes con el módulo falso; suite Karma acotada y completa |
| AC-07 | Specs existentes del sidebar |
**E2E: NO** — se cubre con specs de componentes y guard; no hay herramienta E2E instalada y no se justifica instalarla.

# Implementation Plan
- **Files affected:** frontend `layout/sidebar/sidebar.component.ts` (+spec), `core/guard/module.guard.ts` (+spec), `app.routes.ts` (`data: { module: 'reporting', home: true }` en dashboard), `shared/directives/if-module.directive.ts` (+spec, nuevo), plantillas y specs de `order-list`, `order-form` y `reports`; docs (`design-system.md` §6, `modulos-implementados.md`).
- **Steps:**
  1. Función pura `filterMenu(items, enabled)` en el sidebar: filtra hijos, hereda el módulo del grupo y oculta grupos vacíos (AC-01).
  2. `moduleGuard`: si la ruta lleva `data.home` y el módulo no está habilitado, redirige a `APP_PATHS.catalog` en vez de a la pantalla de error; aplicarlo a la ruta del dashboard (AC-02, AC-03).
  3. Directiva `IfModuleDirective` en `shared/` y reemplazo de los getters `customersDisabled` en las plantillas (los getters se mantienen donde los usa la lógica) (AC-04, AC-05).
  4. Specs y ajuste de los `ModulesService` falsos de los specs afectados (AC-05, AC-06, AC-07).
  5. Docs vivos y verificación (lint, build, Karma).
- **Risks / New dependencies:** ninguna dependencia nueva. Riesgo: bucle de redirección si el destino de «inicio» estuviera deshabilitado (Catálogo es base y no puede estarlo).
