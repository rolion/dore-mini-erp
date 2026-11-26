# PLAN-2026-11-26-crear-iniciar-orden-receta (v1)

**Task:** TASK-crear-iniciar-orden-receta · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** `docs/design/DDR-crear-iniciar-orden-receta-pantallas-ordenes.md`, `docs/adr/ADR-crear-iniciar-orden-receta-agregado-orden-produccion.md`

## Objective
Permitir crear una orden de producción desde una receta activa (almacén + número de preparaciones), ver lo previsto, guardarla como Borrador e iniciarla (En preparación) con fecha y hora, sin tocar existencias.

## Context
Base: rama `produccion` (recetas ya integradas). Ver TASK para hechos y supuestos.

# Specification

## Domain context
Bounded context **Producción** (`modules/production`). Relacionados: Catálogo (nombres/unidades, ya integrado), Inventario (solo lectura de almacenes por `services`).

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Receta | Fórmula: producto resultante, rendimiento base e ingredientes | `domain/recipe.py` |
| Rendimiento | Unidades que produce **una** preparación | tarjeta |
| Preparación | Una vez que se elabora la receta | tarjeta |
| Orden de producción | Plan de producir N preparaciones de una receta en un almacén | tarjeta |
| Previsto | Cantidad por preparación × preparaciones | tarjeta |

## Current behavior
Solo existen recetas (`production/api/views.py:98-134`); no hay órdenes ni ítem de menú (`routes.json:339-363`).

## Expected behavior
Existe el agregado Orden con estados Borrador y En preparación. Crear exige receta activa, almacén activo y preparaciones entero ≥ 1; copia la receta; calcula lo previsto; iniciar pasa a En preparación y registra la fecha y hora. Ninguna de estas operaciones genera movimientos de existencias.

## Domain rules / invariants
- INV-01 (nueva): preparaciones es un entero ≥ 1 (se rechazan 0, negativos, decimales, texto, booleanos).
- INV-02: la receta debe estar activa **al crear**; el producto resultante y los ingredientes de la receta no se revalidan.
- INV-03: la orden guarda copia de receta (nombre, producto resultante, rendimiento) e ingredientes (producto, unidad, cantidad por preparación); no depende de la receta posterior.
- INV-04: previsto total = cantidad por preparación × preparaciones (`Decimal`, 4 decimales); producción prevista = rendimiento × preparaciones.
- INV-05: estados solo por métodos: `DRAFT → IN_PREPARATION` (`start`); `start` fuera de Borrador falla; editar solo en Borrador.
- INV-06: el almacén debe ser un almacén activo de la empresa (al crear, editar e iniciar).
- INV-07: `started_at` se fija al iniciar y no cambia; solo existe en `IN_PREPARATION`.
- INV-08: número correlativo por empresa, sin repetirse (único por `(company_id, number)`).
- INV-09: ninguna operación de esta tarea escribe en Inventario.

## Acceptance criteria
- AC-01: receta de 24 con 5 preparaciones → producción prevista 120 e ingredientes ×5 (en API y pantalla).
- AC-02: crear con receta inactiva o inexistente (o de otra empresa) falla con error en `recipe_id`.
- AC-03: preparaciones inválidas (0, −1, 2.5, "abc", vacío, true) fallan con error en `preparations`.
- AC-04: al editar la receta (ingredientes, rendimiento, nombre) o desactivarla, la orden existente conserva los valores originales.
- AC-05: guardar borrador y editar borrador (almacén/preparaciones, recalculando previsto) no crean movimientos ni cambian saldos.
- AC-06: iniciar desde Borrador → `IN_PREPARATION` con `started_at` registrado; iniciar de nuevo falla (409/400 con mensaje); no cambia existencias.
- AC-07: editar una orden En preparación falla.
- AC-08: almacén inexistente, inactivo o de otra empresa falla con error en `warehouse_id`.
- AC-09: lista paginada con filtro de estado y orden más reciente primero; detalle con ingredientes.
- AC-10: aislamiento por empresa (otra empresa recibe 404) y módulo `production` deshabilitado → 403 `module_disabled`.
- AC-11: el menú muestra «Órdenes de producción» solo con `production` habilitado; el módulo requiere `inventory`.
- AC-12: UI: alta con panel Previsto en vivo, Guardar borrador e Iniciar preparación; detalle con acción Iniciar; estados cargando/vacío/error; i18n es/en/pt.

## Edge cases / Error cases
- EDGE-01: dos creaciones simultáneas no repiten número (contador bloqueado).
- EDGE-02: preparaciones muy grandes: tope `99999` (error de validación).
- EDGE-03: la receta se desactiva entre guardar el borrador e iniciar: se permite iniciar (INV-02).
- EDGE-04: el almacén se desactiva antes de iniciar: iniciar falla con error en `warehouse_id`.
- EDGE-05: producto de la receta ya inactivo: la orden conserva el snapshot; no bloquea.

## Authorization / permissions
Usuario autenticado de la empresa con módulo `production` habilitado; `company_id` sale del usuario (`shared/tenancy.py`).

## API contract
- API-01: `GET /api/production-orders/?status=all|draft|in_preparation&page&page_size` → lista paginada.
- API-02: `POST /api/production-orders/` `{recipe_id, warehouse_id, preparations}` → 201 con el detalle (borrador).
- API-03: `GET /api/production-orders/<id>/`; `PUT` `{warehouse_id, preparations}` (solo borrador).
- API-04: `POST /api/production-orders/<id>/start/` → detalle `IN_PREPARATION`.
- API-05: `GET /api/production-orders/warehouses/` → almacenes activos `{id, name, is_default}`.
- Detalle: `id, number, status, recipe {id, name}, result_product {id, name, unit {id, abbreviation}}, warehouse {id, name}, preparations, yield_per_preparation, expected_output, ingredients [{product_id, product_name, unit_id, unit_abbreviation, quantity_per_preparation, expected_quantity}], created_at, started_at`. Cantidades como string con 4 decimales. Aditivo: no cambia contratos existentes.

## UI behavior
- UI-01: lista (DDR; plantilla `purchase-list`). UI-02: alta/edición con panel Previsto (`purchase-form`). UI-03: detalle con acciones en cabecera (`purchase-detail`) y tarjetas bajo 957 px. UI-04: ítem de menú. Estados y avisos según DDR.

## Non-functional requirements
`Decimal` en todo cálculo; sin `any`; sin texto hardcodeado; Reactive Forms; lint limpio en lo cambiado.

## Out of scope
Cancelar/eliminar borradores, completar la orden, consumo real de ingredientes, entrada del producto terminado, lotes, costos, impresión, cambio de receta en un borrador.

## Open questions
Confirmar con negocio (no bloquean; ver supuestos 1-6 del TASK): edición de borradores limitada a almacén/preparaciones, receta activa solo al crear, número `OP-0001`.

# Test Specification

## Unit tests
Dominio `ProductionOrder`: INV-01, 03, 04, 05, 07, ejemplo 24×5.
## Integration tests
API con `APITestCase` (patrón de `production/tests/test_api.py`): AC-01 a AC-10, EDGE-01 (numeración), EDGE-03/04; AC-05/06 comparando saldos de Inventario antes y después. Guardas: `test_guards`, `test_boundaries`, modularidad (AC-11 backend).
Frontend (Karma): servicio API, formulario (previsto en vivo, validación, botones), lista, detalle (acciones por estado), menú (AC-11), paridad de claves i18n.
## E2E
**NO** — el flujo se cubre con pruebas de API y de componentes; no hay Playwright en el proyecto y no se agrega dependencia.
## Regression tests
Se ejecutan las suites existentes de `production`, `modularity`, `inventory` y la de límites.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | unit dominio + API + spec del formulario |
| AC-02, AC-03, AC-08 | API tests |
| AC-04 | API test (editar/desactivar receta y releer la orden) |
| AC-05, AC-06 | API tests con saldos de Inventario sin cambio |
| AC-07 | dominio + API |
| AC-09, AC-10 | API tests (lista, 404 entre empresas, 403 módulo) |
| AC-11 | tests de modularidad y de menú |
| AC-12 | specs de componentes + `npm run i18n:check` |

# Implementation Plan

## Architecture considerations
Ver ADR: agregado con snapshot, contador por empresa, puerto `WarehouseDirectory` sobre `inventory.services`.

## Proposed solution
Capas en `backend/modules/production/`: `domain/production_order.py`; `application/orders.py` (`ProductionOrders`, puertos `RecipeSource`, `WarehouseDirectory`, `OrderRepository`, `Clock`); `infrastructure/django/models.py` + `repositories.py` (+ adaptadores en `adapters.py`); `api/order_views.py`, `order_serializers.py`, `order_urls.py`.

## Files/components affected
- Backend: archivos anteriores; `config/urls.py` (`api/production-orders/`); `modularity/domain/modules.py` (`requires`); migración `0002`; `modules/accounts/test_guards.py`; `sales/tests/test_boundaries.py`; `modularity/tests/test_domain.py`; tests nuevos en `production/tests/`.
- Frontend: `features/production/{models,services,pages/order-list,order-form,order-detail}`, `production.routes.ts`, `app.routes.ts`, `assets/data/routes.json`, `assets/i18n/{es,en,pt}.json`, specs.
- Docs: `docs/architecture/ddd.md` (nota Producción).

## Implementation steps
1. Dominio y pruebas unitarias (INV-01..07). 
2. Modelos, migración `0002`, repositorio con contador bloqueado (INV-08).
3. Casos de uso, adaptadores (recetas y almacenes) y guardas/límites/modularidad (AC-11).
4. API y pruebas de integración (AC-01..AC-10).
5. Frontend: modelos, servicio, lista, formulario, detalle, rutas, menú, i18n (AC-12).
6. Documentación (`ddd.md`), lint (`ruff`, `flake8`, `npm run lint`), suites completas.

## Database / migrations
Nueva `0002_productionorder...` (tablas `production_order`, `production_order_ingredient`, `production_order_counter`); no se edita `0001`.

## Risks
Acoplamiento con Inventario (mitigado en ADR); concurrencia de numeración (bloqueo); empresas con Producción sin Inventario.

## New dependencies
Ninguna.
