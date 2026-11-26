# TASK-gestionar-recetas-produccion: Gestionar recetas de producción

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-gestionar-recetas-produccion (base: `produccion`)
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/127
**Fuente:** https://trello.com/c/s8CrL2N0/1-dore-prod-001-gestionar-recetas-de-producci%C3%B3n

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-26 | (nuevo) → INVESTIGATION | Task creado desde la tarjeta DORE-PROD-001 | delivery-start |
| 2026-11-26 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | Veredicto NEEDS_ARCHITECTURE, diseño SI | delivery-start |
| 2026-11-26 | PLANNING → ENGINEERING | Specification READY, PR abierto contra `produccion` | delivery-start |
| 2026-11-26 | ENGINEERING → REVIEW | Implementación completa del plan v1 | delivery-build |
| 2026-11-26 | REVIEW → PUBLISH | Quality Gate ciclo 1 PASS (1 Medium y 6 Low abiertos) | delivery-publish |
| 2026-11-26 | PUBLISH → REVIEW → PUBLISH | Correcciones REV-02..07 y Quality Gate ciclo 2 PASS | delivery-publish |

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
Implementado el plan v1 sin cambios de Specification.

**Backend** (`backend/modules/production/`, nuevo): dominio `Recipe`/`RecipeIngredient` (INV-01, INV-03..INV-06), casos de uso `RecipeBook` con puerto `ProductCatalog` (INV-02, INV-04), repositorio por `company_id` (INV-07), modelos y migración `0001_initial` (nombre único sin distinguir mayúsculas, cantidades > 0), API `/api/recipes/` (AC-01..AC-08), fachada `catalog.services.get_products_for_production`, módulo `production` en el catálogo de módulos (requiere `catalog`, no habilitado por defecto; AC-09). Guardas actualizadas: `accounts/test_guards.py`, `sales/tests/test_boundaries.py`, `modularity/tests`.

**Frontend** (`features/production/`, nuevo): modelos, `RecipesApiService`, lista, formulario con líneas, detalle, `RecipeToggleComponent`, ruta `production/recipes` con `moduleGuard`, menú «Producción › Recetas» en `routes.json` e i18n es/en/pt (AC-03..AC-04, AC-09, AC-10). Referencias seguidas: `features/services` (lista/detalle/activar) y `features/inventory/pages/stock-opening` (selector de producto con búsqueda y líneas). Reutiliza `ProductsApiService`, `unsavedChangesGuard`, `provideTestTranslations`, badges y botones `btn-tbl-*`; no se crearon componentes compartidos nuevos.

**Pruebas:** backend `modules/production/tests/test_domain.py` y `test_api.py` (AC-01..AC-09, fachada, aislamiento entre empresas); frontend `recipes-api.service.spec.ts`, `recipe-pages.spec.ts` y `sidebar-menu.spec.ts`. E2E: no, como el plan.

**Desviaciones respecto al plan (sin tocar la Specification):**
- API en `snake_case` (como el resto de Catálogo/Servicios) en lugar de camelCase en API-01..API-05; los nombres de campo son un detalle de formato, el contenido y las reglas no cambian.
- El módulo `production` no declara `optional=('inventory',)` (no hay integración todavía); se actualizó el ADR.
- La lista usa una tabla con `table-responsive` (scroll horizontal en pantallas estrechas) en vez de la variante de tarjetas bajo 992 px que mencionaba el DDR; queda como deuda visual menor.
- `PUT` valida primero forma y tipos del cuerpo (400) y después busca la receta (404 si es de otra empresa); un cuerpo inválido da 400 antes que 404, sin filtrar datos entre empresas.

**Deuda técnica:** variante compacta de tarjetas para la lista; el selector de producto busca los primeros 20 coincidentes (typeahead), sin paginación infinita.

**Notas de verificación (no es el Quality Gate):** suite de frontend completa en verde (1870 pruebas), `npm run i18n:check` sin faltantes, `tsc` sin errores, `ruff`/`flake8` limpios en `modules/production`. Backend: ver Review.

## Review
**Quality Gate ciclo 2: PASS** (HEAD `c6f7789b`, subagente aislado): backend 303 OK (production, catalog, modularity, accounts, límites), `makemigrations --check` sin cambios, bandit limpio; frontend 1872 OK (líneas 89,2 %), lint, `i18n:check`, build y `npm audit` OK. Verificadas REV-02, 03, 05, 06, 07; REV-04 parcial (abierto); REV-01 abierto a la espera de decisión del usuario. Hallazgos nuevos Low: N-01 (ADR desactualizado, corregido) y N-02 (DDR contradictorio, corregido); N-03 `focusFirstError()` sin prueba unitaria directa (abierto). Revisión visual en navegador: no verificada.

**Quality Gate ciclo 1: PASS** (subagente aislado, 2026-11-26). Sin hallazgos Critical/High.

Ejecutado: backend `modules.production/catalog/modularity/accounts/sales.test_boundaries` 298 OK (más suite completa 2517 OK del implementador); `makemigrations --check` sin cambios; ruff/flake8 sin avisos en `modules/production` (5 E501 preexistentes en líneas ya largas); bandit sin salida; frontend `ng test --code-coverage` 1870 OK (líneas 89,18 %, ramas 78,43 %); `npm run lint` OK; `i18n:check` 0 faltantes; `npm run build` OK; `npm audit` 0 vulnerabilidades.
**No realizado:** revisión visual en navegador (móvil/escritorio, claro/oscuro) y prueba manual contra servidor levantado.

Hallazgos (todos Open, no bloquean): REV-2026-11-26-gestionar-recetas-produccion-01 (Medium, SPECIFICATION: contrato API en snake_case vs camelCase de API-01..05; enmendar requiere aprobación del usuario), -02 a -07 (Low: mensaje de resultado-como-ingrediente, aviso en formulario, desviaciones del DDR, huecos de prueba backend, texto 404/400 del PUT, descripción del módulo).

## Publicación
PR #127 listo para aprobación humana contra `produccion`; no se mergea. Cambios con base de datos (migración nueva `production/0001_initial`) y ADR: requieren revisión humana. Pendiente: decidir REV-01 (Specification) y los Low.
