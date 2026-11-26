# PLAN-2026-11-26-gestionar-recetas-produccion (v1)

**Task:** TASK-gestionar-recetas-produccion · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-gestionar-recetas-produccion-pantallas-recetas · ADR-gestionar-recetas-produccion-modulo-production

## Objective
Permitir crear, consultar, editar y activar/desactivar recetas de producción (producto resultante, rendimiento base e ingredientes) con un módulo opcional `production` y el menú Producción → Recetas.

## Context
Tarjeta Trello DORE-PROD-001; ver el TASK. La base del PR es la rama `produccion`.

# Specification

## Domain context
Nuevo bounded context **Production**. Depende de Catálogo (lectura vía `catalog.services`); respeta las reglas de unidad de Inventario sin importarlo.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Receta | Fórmula con nombre, producto resultante, rendimiento base e ingredientes | Tarjeta |
| Producto resultante | Producto del catálogo que se obtiene | Tarjeta |
| Rendimiento base | Cantidad del producto resultante por preparación, en su unidad base | Tarjeta («24 cuñapés») |
| Ingrediente | Producto del catálogo con cantidad y unidad | Tarjeta |
| Unidad compatible | Unidad base del producto, sin conversión | Supuesto (INV-04) |

## Current behavior
No existe producción ni menú (ver TASK).

## Expected behavior
Con el módulo habilitado, la persona gestiona recetas desde Producción → Recetas. Una receta activa queda disponible para futuras órdenes; editar/desactivar no borra ni altera nada histórico (no hay borrado).

## Domain rules / invariants
- INV-01 Nombre obligatorio, ≤150 caracteres, único por empresa sin distinguir mayúsculas.
- INV-02 Producto resultante existente en la empresa, activo y con unidad base.
- INV-03 Rendimiento base > 0 (≤ 4 decimales); fracciones solo si la unidad del resultado las admite.
- INV-04 Cada ingrediente: producto existente, activo, con unidad base; `unit_id` = unidad base del producto; cantidad > 0 (≤ 4 decimales; sin fracciones si la unidad no las admite).
- INV-05 ≥1 ingrediente; un producto no se repite; el producto resultante no puede ser su propio ingrediente.
- INV-06 Receta nueva queda activa. Estados cambian por `activate()`/`deactivate()` (idempotentes). No existe eliminación.
- INV-07 Toda consulta filtra por `company_id` del usuario autenticado.

## Acceptance criteria
- AC-01 Crear receta válida (p. ej. «Queso» → cuñapé a granel, rendimiento 24, ingredientes con cantidades) la guarda activa y aparece en el listado.
- AC-02 Se rechazan con error por campo: nombre vacío/duplicado, resultado inexistente/de otra empresa/inactivo/sin unidad, rendimiento ≤ 0 o con fracción no admitida, sin ingredientes, ingrediente repetido, igual al resultado, cantidad ≤ 0 o fraccionaria no admitida, unidad distinta de la base.
- AC-03 El listado muestra receta, producto resultante, rendimiento base (con unidad) y estado; filtra por estado (Activos por defecto) y busca por nombre; paginado.
- AC-04 El detalle muestra datos e ingredientes (producto, cantidad, unidad).
- AC-05 Editar reemplaza nombre, resultado, rendimiento e ingredientes con las mismas validaciones; el id y la fecha de creación se conservan.
- AC-06 Activar y desactivar cambian solo el estado y son idempotentes; una receta desactivada se conserva con todos sus datos y se puede reactivar.
- AC-07 No hay endpoint de borrado (DELETE → 405).
- AC-08 Una receta de otra empresa responde 404; un usuario sin empresa, 403; sin sesión, 401.
- AC-09 Con el módulo `production` deshabilitado la API responde 403 `module_disabled`, el menú no se muestra y la ruta lleva a `/module-disabled`; habilitarlo exige Catálogo.
- AC-10 El menú Producción → Recetas existe con textos es/en/pt; no aparece «Órdenes».

## Edge cases / Error cases
- EDGE-01 Doble envío o nombre con espacios/mayúsculas distintas → duplicado detectado tras `strip` y sin distinguir caso.
- EDGE-02 Cantidades con más de 4 decimales o no numéricas → 400; nunca `float`.
- EDGE-03 `page`/`page_size` inválidos → 400 como en Servicios.
- EDGE-04 Edición concurrente: gana la última escritura (sin versionado).
- EDGE-05 Producto de la receta desactivado/cambiado de unidad después: la receta se muestra con aviso; guardar de nuevo exige corregirlo.

## Authorization / permissions
Usuario autenticado con empresa y módulo habilitado (mismo criterio que Catálogo); la empresa sale del usuario (`shared/tenancy.py`), nunca del cuerpo.

## API contract
- API-01 `GET /api/recipes/?status=active|inactive|all&q=&page=&page_size=` → `{count,next,previous,results:[{id,name,resultProduct:{id,name,unit:{id,abbreviation}},yieldQuantity,active}]}`.
- API-02 `POST /api/recipes/` cuerpo `{name,resultProductId,yieldQuantity,ingredients:[{productId,unitId,quantity}]}` → 201 con el detalle.
- API-03 `GET /api/recipes/<id>/` → detalle (+ `ingredients:[{productId,productName,unitId,unitAbbreviation,quantity,productActive}]`, `createdAt`, `updatedAt`).
- API-04 `PUT /api/recipes/<id>/` mismo cuerpo que API-02 → 200.
- API-05 `POST /api/recipes/<id>/activate/` y `/deactivate/` → 200 con el detalle.
Cantidades como cadenas decimales; errores `{campo: [mensajes]}` y `ingredients: [{...}]` por línea, como el resto de la API. Aditivo.

## UI behavior
- UI-01 Menú «Producción» (módulo `production`) con «Recetas».
- UI-02 Lista según plantilla «Lista» (DDR); estados cargando/vacío/error.
- UI-03 Formulario con líneas de un solo paso: unidad del ingrediente y del rendimiento mostradas de solo lectura al elegir el producto; errores por campo y por línea.
- UI-04 Detalle con ingredientes, aviso EDGE-05 y acciones Editar / Activar-Desactivar / Volver.

## Non-functional requirements
Dinero no interviene; cantidades en `Decimal`. i18n es/en/pt con las mismas claves. Sin consultas N+1 en la lista (`select_related`/prefetch o lote vía fachada).

## Out of scope
Órdenes de producción, consumo/producción de existencias, costeo, empaques, conversiones de unidades, versionado de recetas, carga inicial del ejemplo de queso.

## Open questions
Ninguna que bloquee; si negocio quiere conversión de unidades o roles específicos, será otra tarea.

# Test Specification

## Unit tests
Dominio (`Recipe`: INV-01..INV-06, activar/desactivar idempotente); validadores de cantidad con `Decimal`. Frontend: servicio API, formulario (validación, línea repetida, unidad derivada), claves i18n.

## Integration tests
API con DB de test: AC-01..AC-09 (incluye aislamiento entre dos empresas, módulo deshabilitado, DELETE 405); fachada de Catálogo `get_product_for_production`; migración.

## E2E
**NO** — no hay flujo crítico de punta a punta ni dependencia nueva (sin Playwright); cubren las pruebas de API y de componentes.

## Regression tests
`modularity` (catálogo de módulos), `accounts/test_guards`, pruebas de i18n (`npm test`, `npm run i18n:check`), sidebar-menu.spec, snapshot de defaults sin cambios.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01, AC-02 | domain + API tests; spec del formulario |
| AC-03, AC-04 | API (lista/detalle, filtros, paginación); specs de lista y detalle |
| AC-05, AC-06 | API (PUT, activate/deactivate idempotente) |
| AC-07, AC-08 | API (405, aislamiento, 401/403) |
| AC-09 | modularity + API `module_disabled`; sidebar y `moduleGuard` spec |
| AC-10 | sidebar-menu.spec e i18n test |

# Implementation Plan

## Architecture considerations
Ver ADR: módulo propio, UUID sin FK entre módulos, fachada de Catálogo, sin borrado.

## Proposed solution
Backend `modules/production/{domain,application,infrastructure,api}` modelado sobre `service_catalog`; frontend `features/production/` modelado sobre `features/services`.

## Files/components affected
- Backend: `modules/production/**` (nuevo), `modules/catalog/services.py` (fachada), `modules/modularity/domain/modules.py`, `config/settings/base.py`, `config/urls.py`, `modules/accounts/test_guards.py`, migración `production/0001_initial`, `docs/architecture/ddd.md`.
- Frontend: `features/production/**` (nuevo), `app.routes.ts`, `assets/data/routes.json`, `assets/i18n/{es,en,pt}.json`.
- Docs: `design-system.md` §6.

## Implementation steps
1. Fachada `get_product_for_production` + pruebas (INV-02/04).
2. Dominio `Recipe`/`RecipeIngredient` + pruebas (INV-01..06).
3. Modelos, migración, repositorio por `company_id` (INV-07).
4. Casos de uso y puerto `ProductCatalog` con su adaptador.
5. API: serializers, vistas, URLs; registrar app y módulo `production` (AC-01..AC-09).
6. Frontend: modelos y servicio API; lista; formulario con líneas; detalle; rutas con `moduleGuard`; menú e i18n (AC-03..AC-04, AC-10).
7. Actualizar `ddd.md`, `design-system.md`, guards; ejecutar pruebas, lint y `i18n:check`.

## Database / migrations
Una migración nueva `production/0001_initial`; no se toca ninguna migración existente.

## Risks
EDGE-05 (productos cambiados después); módulo nuevo en el registro puede afectar pruebas que cuentan módulos (se ajustan).

## New dependencies
Ninguna.
