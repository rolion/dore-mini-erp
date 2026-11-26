# TASK-gestionar-recetas-produccion: Gestionar recetas de producción

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-gestionar-recetas-produccion (base: `produccion`)
**Pull Request:** _se completa al abrirlo_
**Fuente:** https://trello.com/c/s8CrL2N0/1-dore-prod-001-gestionar-recetas-de-producci%C3%B3n

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-26 | (nuevo) → INVESTIGATION | Task creado desde la tarjeta DORE-PROD-001 | delivery-start |
| 2026-11-26 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | Veredicto NEEDS_ARCHITECTURE, diseño SI | delivery-start |
| 2026-11-26 | PLANNING → ENGINEERING | Specification READY, PR abierto contra `produccion` | delivery-start |

## Investigación

### Requerimiento
Fuente: tarjeta Trello DORE-PROD-001 (lista «En curso», tablero «produccion dore»). Insumo, no Specification aprobada. Aclaración del usuario: «usa la rama produccion» (la base del PR es `produccion`, no `main`).

- **Historia:** como responsable de producción, definir y mantener recetas para fabricar cantidades consistentes con los productos del catálogo.
- El menú **Producción** incluye Recetas y Órdenes de producción; Recetas permite crear, consultar, editar y activar/desactivar fórmulas usando el catálogo y las unidades de Inventario.
- Cada receta: nombre, producto resultante existente, rendimiento base positivo y ≥1 ingrediente con cantidad positiva y unidad compatible con Inventario.
- Listado: receta, producto resultante, rendimiento base y estado. Receta activa = disponible para nuevas órdenes.
- Ejemplo: receta de queso produce 24 cuñapés a granel por preparación; los empaques se gestionan después.
- Editar o desactivar una receta conserva la información de las órdenes históricas.
- Sin dependencias de otras tarjetas; reutiliza catálogo y unidades de medida.
- Sin checklists ni comentarios.

### Hechos encontrados
- No existe módulo de producción: sin coincidencias de «receta/recipe/production» en `backend/modules/` ni en `frontend/panel_admin/src/app/` (solo coincidencias ajenas en `reporting/application/criteria.py`). Hay que crear el contexto y el menú **Producción**.
- `origin/produccion` apunta hoy al mismo commit que `origin/main` (`0d05db92`); la rama de trabajo parte de ahí.
- Catálogo de módulos: `backend/modules/modularity/domain/modules.py:15-38` (`ModuleDefinition` con `requires`/`optional`); `DEFAULT_ENABLED_KEYS` en `:43`. Los módulos opcionales se activan por empresa; el snapshot de defaults (`backend/shared/company_defaults/snapshot.json:337-352`) lista los módulos habilitados por defecto.
- Producto: `backend/modules/catalog/domain/product.py:60-80` — `active`, `tracks_stock`, `base_unit_id`/`base_unit` (`UnitSummary`), `category`, `can_buy`, `can_sell`. La categoría no restringe usos.
- Unidad de medida: `backend/modules/catalog/domain/unit.py:32-42` — `allows_fractions`, `active`. Inventario trabaja con **una unidad base por producto**, sin tabla de conversiones; la regla de cantidades es `inventory/domain/stock.py:59-62` (`check_quantity_for_unit`: sin fracciones si la unidad no las admite).
- Otros módulos consumen Catálogo solo por su fachada `backend/modules/catalog/services.py` (DTO congelados, p. ej. `ProductForPurchase`, `:41-65`).
- Registro de un módulo: `INSTALLED_APPS` en `backend/config/settings/base.py:23-24`, rutas en `backend/config/urls.py:21-27` (`api/services/` → `service_catalog.api.urls`).
- Implementación de referencia backend (CRUD con activar/desactivar, paginación 20/100, validación `page`): `backend/modules/service_catalog/` (`api/views.py:1-40`, `api/urls.py`, `domain/service.py`, `infrastructure/django/repositories.py`).
- Referencia frontend: `frontend/panel_admin/src/app/features/services/` (lista, formulario, detalle, `services-api.service.ts`, `services.routes.ts`) y rutas por módulo con `moduleGuard` en `frontend/panel_admin/src/app/app.routes.ts:257-372`.
- Sistema de diseño: `docs/design/design-system.md` §5 (plantillas Lista, Formulario, Detalle, «Formulario con líneas») y §6 (menú dinámico por `assets/data/routes.json` con `module`).
- Guardas de arquitectura: `backend/modules/accounts/test_guards.py:6` lista `BUSINESS_APPS`; los módulos de negocio filtran por `company_id`.

### Hipótesis / supuestos no confirmados
- «Unidad compatible con Inventario» = la unidad base del producto ingrediente (no hay conversiones). Se adopta esa regla y se documenta (INV-04); si negocio quisiera conversiones sería otra tarea.
- Los permisos son los de los demás módulos de catálogo (usuario autenticado de la empresa, con módulo habilitado); la tarjeta no pide roles.
- Las órdenes de producción (tarjeta posterior) copiarán la receta al crearse; por eso aquí no existe borrado de recetas (solo desactivar).
- El ejemplo de queso/cuñapés es un dato de prueba, no una carga inicial.

### Módulos y dependencias relacionadas
Catálogo (productos y unidades; solo lectura vía fachada), Inventario (reglas de unidad/fracciones; sin dependencia de código), Modularidad (registro del módulo), frontend `products`, layout/sidebar y `routes.json`.

### Implementaciones similares existentes
`service_catalog` (backend) y `features/services` (frontend): lista paginada con filtro de estado, formulario, detalle, activar/desactivar. `features/inventory/pages/stock-opening` para el formulario con líneas.

### Comportamiento actual
No se pueden definir recetas ni existe menú Producción.

### Restricciones
`CLAUDE.md`: aislamiento por `company_id`, dominio sin Django, `Decimal` (cantidades), migraciones nuevas, i18n es/en/pt sin texto hardcodeado, Reactive Forms, sin dependencias nuevas sin aviso.

### Riesgos identificados
- Producto ingrediente/resultante que luego se desactiva o cambia de unidad base: la receta guardada queda con datos vistos «en vivo»; se muestra aviso en el detalle (EDGE-05).
- Órdenes futuras necesitan receta inmutable: se resuelve copiándola al crear la orden (fuera de alcance, ya anticipado en el ADR).

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — nuevo bounded context/módulo (tablas, API, módulo opcional del catálogo de módulos, menú) que depende de Catálogo.

### Diseño requerido
**SI** — pantallas nuevas (lista, formulario con líneas, detalle) y una entrada de menú nueva.

## Diseño
DDR: `docs/design/DDR-gestionar-recetas-produccion-pantallas-recetas.md`.

## Arquitectura
ADR: `docs/adr/ADR-gestionar-recetas-produccion-modulo-production.md`.

## Plan
`docs/plans/PLAN-2026-11-26-gestionar-recetas-produccion.md` (v1, COMPLETO). Specification readiness: **READY**.

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
