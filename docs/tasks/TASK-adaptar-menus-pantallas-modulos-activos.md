# TASK-adaptar-menus-pantallas-modulos-activos: Adaptar menús y pantallas a los módulos activos (PB-MOD-003)

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** SI
**Rama:** task/TASK-adaptar-menus-pantallas-modulos-activos (creada desde `task/TASK-habilitar-modulos-por-empresa`, que contiene PB-MOD-001 y PB-MOD-002; ver PR #17)
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/18 (apilado sobre PR 17)

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-27 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-10-27 | INVESTIGATION → DESIGN → PLANNING | NEEDS_PLAN: solo frontend, sin cambio de API ni permisos; un flujo de inicio cambia | delivery-start |
| 2026-10-27 | PLANNING → ENGINEERING | Specification READY tras respuestas del usuario | delivery-start |
| 2026-10-27 | ENGINEERING → REVIEW | Implementación completa según plan v1 | delivery-build |

## Investigación

### Requerimiento
PB-MOD-003 · Adaptar menús y pantallas a los módulos activos (Modularidad, P0, depende de PB-MOD-001 y PB-MOD-002). Como usuario, quiero ver las funciones habilitadas para trabajar con una interfaz acorde a mi negocio.
- Menú lateral: conservar los accesos actuales y añadir Inventario, Compras y Configuración según el mapa de navegación; cada grupo muestra solo sus hijos habilitados.
- Vistas: página inicial existente, navegación lateral, encabezado con ruta de navegación y pantalla de acceso no disponible; no se crea un dashboard paralelo.
- Datos visibles: nombre de la empresa y usuario actuales; etiqueta y elemento activo del menú. Contadores o tarjetas solo cuando su fuente está habilitada.
- Aceptación de interfaz: con Inventario deshabilitado no aparecen almacenes ni stock en formularios de ventas/compras; al habilitarlo se muestran los campos aplicables. Todas las pantallas usan los componentes, tipografía, colores, tablas, formularios y mensajes ya establecidos.
- AC: (1) menús y accesos muestran solo los módulos activos y sus configuraciones permitidas; (2) una URL guardada de un módulo deshabilitado muestra un mensaje claro y permite volver a una pantalla válida; (3) Ventas conserva el flujo actual cuando Inventario está deshabilitado y los paneles no muestran errores por módulos ausentes.

**Decisiones del usuario (2026-10-27):**
1. **Inicio sin Reportes:** el panel inicial pasa a ser la primera pantalla habilitada (Catálogo, que es base). Login, logo, iconos de inicio y la URL guardada del dashboard llevan allí sin mensaje de error; las demás URLs de módulos deshabilitados siguen mostrando «Módulo no habilitado».
2. **Campos de Inventario:** no se inventan campos (no existen); se crea un mecanismo reutilizable (`*appIfModule`) probado y usado ya en lo existente (controles de Clientes). Los campos de almacén y stock se agregarán con la historia de Inventario.
3. **Entrega previa:** PB-MOD-002 no llegó a `main` (el PR #16 se mergeó hacia la rama ya mergeada del PR #15); se reentrega con el PR #17, sobre el que esta tarea se apila.

### Hechos encontrados
- `frontend/panel_admin/src/app/layout/sidebar/sidebar.component.ts:30-32,111-117` — `isVisible` solo filtra ítems de primer nivel por `module`; los hijos de un grupo (`submenu`) no se filtran ni se oculta un grupo sin hijos visibles.
- `frontend/panel_admin/src/assets/data/routes.json` — grupos: Catálogo (`catalog`), Gastos (`expenses`), Configuración (sin módulo, hijo «Módulos»); Inventario, Compras y Configuración › Módulos ya existen (PB-MOD-001).
- `frontend/panel_admin/src/app/layout/sidebar/sidebar.component.html:5,29-33` — el logo enlaza a `/pocketbiz/dashboard/main`; el panel de usuario muestra nombre y empresa; ítems activos con `routerLinkActive`.
- `frontend/panel_admin/src/app/core/guard/module.guard.ts` — redirige a `/pocketbiz/module-disabled?module=<clave>` cuando el módulo no está habilitado (PB-MOD-002), también para el dashboard.
- `frontend/panel_admin/src/app/authentication/signin/signin.component.ts:11` y `signup.component.ts:16` — el destino tras login/registro es `APP_PATHS.dashboard`; `app.routes.ts:26` redirige `''` a `dashboard/main`; con Reportes deshabilitado el login aterrizaría en «Módulo no habilitado».
- Unas 13 pantallas de negocio (`features/*/pages/*`) y `coming-soon`/`module-list` llevan el icono de inicio del breadcrumb fijo a `/pocketbiz/dashboard/main`.
- `frontend/panel_admin/src/app/features/sales/pages/order-list/order-list.component.ts`, `order-form/order-form.component.ts` y `reporting/pages/reports/reports.component.ts` — ocultan los controles de Clientes con un getter `customersDisabled` (PB-MOD-002, DDR integraciones opcionales).
- `frontend/panel_admin/src/app/features/reporting/pages/dashboard/dashboard.component.ts:41-43` — el dashboard pide solo `dashboard` y `pending` (Ventas y Gastos, que Reportes exige).
- `frontend/panel_admin/src/app/core/routing/app-paths.ts` — constantes de rutas absolutas (`dashboard`, `catalog`, `moduleDisabled`).
- No existen campos de almacén ni stock en ningún formulario (Inventario y Compras son un placeholder «Próximamente»).

### Hipótesis / supuestos no confirmados
- «Primera pantalla habilitada» es siempre Catálogo cuando Reportes está apagado (Catálogo es base y el primer ítem del menú tras el dashboard).
- Las pantallas de plantilla (demo) no se tocan: no son parte del producto.

### Módulos y dependencias relacionadas
`modularity` (fuente de la selección), shell de Angular (sidebar, guard, rutas), módulos de negocio solo en sus controles de integración opcional.

### Implementaciones similares existentes
`isVisible` y el filtro del sidebar (PB-MOD-001), `moduleGuard` (PB-MOD-002), ocultamiento de controles de Clientes (PB-MOD-002).

### Comportamiento actual
El menú oculta ítems de primer nivel de módulos deshabilitados; los hijos y la página inicial no se adaptan.

### Restricciones
Sin dependencias nuevas; sin cambios de API; las pantallas reutilizan componentes del sistema de diseño; `CLAUDE.md`: Angular sin `any`, sin suscripciones colgadas.

### Riesgos identificados
- Redirigir el dashboard no debe crear bucles con «Volver al inicio».
- Cambiar los specs que usan un `ModulesService` falso al introducir la directiva.

### Veredicto de complejidad
**NEEDS_PLAN** — cambio acotado al frontend sin contrato API, permisos ni arquitectura nueva.

### Diseño requerido
**SI** — cambia el flujo de inicio y la visibilidad de grupos del menú (riesgo de inconsistencia visual).

## Diseño
Ver `docs/design/DDR-adaptar-menus-pantallas-modulos-activos-inicio-y-menu.md`.

## Arquitectura
No aplica según veredicto.

## Plan
`docs/plans/PLAN-2026-10-27-adaptar-menus-pantallas-modulos-activos.md` (v1, COMPACTO, Specification READY).

## Implementación
**Resumen.** Frontend únicamente: `filterMenu` (`layout/sidebar/menu-filter.ts`) filtra hijos y oculta grupos vacíos; `moduleGuard` trata la ruta con `data.home` (el dashboard) redirigiendo a Catálogo sin pantalla de error; nueva directiva `*appIfModule` (`shared/directives/if-module.directive.ts`) que reemplaza los getters `customersDisabled` en las plantillas de lista y formulario de pedidos y de Reportes.

**Cobertura.**
- AC-01: `menu-filter.spec.ts` (módulo propio y heredado, grupo vacío, grupos sin módulo, módulos sin cargar).
- AC-02: `module.guard.spec.ts` (home deshabilitado → Catálogo, habilitado → pasa).
- AC-03: specs existentes de `moduleGuard` y `ModuleDisabledComponent`, sin cambios.
- AC-04: `if-module.directive.spec.ts` (sin cargar, habilitado, deshabilitado, alternancia).
- AC-05, AC-06: specs de lista y formulario de pedidos y de Reportes con el módulo falso (`enabledKeys$`); no existen campos de almacén ni stock que ocultar.
- AC-07: specs existentes del sidebar (nombre, empresa, ítem activo) sin cambios.

**Desviaciones respecto al plan.** Ninguna. Los getters `customersDisabled` se conservan en `order-list` y `order-form` porque la lógica (no solo la plantilla) los usa; en `reports` se eliminó.

**Pantalla de referencia / componentes.** Sin pantallas nuevas; se reutiliza el menú del sistema de diseño §6. Componente compartido nuevo: `IfModuleDirective` (anotado en `design-system.md` §6).

**Verificación propia (no es el Quality Gate).** `npm run lint` y `npm run build` OK; Karma completo excluyendo `app.component.spec.ts` (no compila en `main`): 71 fallos «should create» de pantallas demo preexistentes y 512 aciertos. Sin backend. No se hizo inspección en navegador.

**Deuda técnica.** Los 71 specs demo rotos y `app.component.spec.ts`; el estilo global de `btn-primary` en el tema oscuro (foco/hover).

**Ciclo 2 (tras el primer FAIL).** REV-01 (High, IMPLEMENTATION): con Clientes habilitado y Ventas deshabilitado, el detalle de cliente pedía `/api/orders/` y el interceptor llevaba a «Módulo no habilitado». Corregido: `CustomerDetailComponent` no pide el historial si Ventas está deshabilitado y el panel usa `*appIfModule="'sales'"`; spec nueva. Desviación respecto al plan: el plan solo listaba los controles de Clientes; el criterio AC-06 («los paneles no muestran errores por módulos ausentes») exigía cubrir también esta integración opcional de Ventas. Verificación propia (no es el Quality Gate): lint y build OK; Karma completo excluyendo `app.component.spec.ts`: 71 fallos preexistentes de pantallas demo y 513 aciertos.

## Review
**Ciclo 1: FAIL** (REV-01 High). El resto de la revisión: lint, build y 512 aciertos de Karma sin fallos nuevos; `modularity` 24 tests OK; AC-01..07 cumplidos; `npm audit` no realizado; inspección en navegador no verificada.
_El ciclo 2 queda pendiente._

## Publicación
_Pendiente_
