# PLAN-2026-10-29-inventario-existencias-filtros-accesos-operativos (v1)

**Task:** TASK-inventario-existencias-filtros-accesos-operativos · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** `docs/design/DDR-inventario-existencias-filtros-accesos-operativos-filtros-detalle-y-retorno.md` / Ninguno

## Objective
Ampliar Inventario → Existencias con clasificación y usos del producto (leídos de Catálogo), filtros combinables por esos datos y accesos a «Registrar apertura» y «Registrar ajuste» desde el detalle, con producto/almacén preseleccionados y retorno al mismo detalle. Sin endpoints nuevos de movimientos ni cambios de reglas de apertura/ajuste.

## Context
Ver TASK. PB-CAT-001 (en `main`) añadió a `ProductModel` `category` (nullable: `null` = sin clasificar/por revisar), `can_buy`, `can_sell` y el filtro de lista de Catálogo; `catalog.services` aún no los entrega a Inventario.

# Specification

## Domain context
Bounded context **Inventory** (existencias, apertura, ajustes); lee de **Catalog** solo vía `catalog.services` (adaptador `inventory/infrastructure/adapters.py`).

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Clasificación / categoría | `raw_material`, `packaging`, `intermediate`, `finished`, `merchandise` o ninguna (sin clasificar) | Catalog (`domain/product.py` `CATEGORIES`) |
| Comprable / Vendible | `can_buy` / `can_sell` del producto; independientes, pueden ser ambos o ninguno | Catalog |
| Posición | par producto/almacén con su saldo | Inventory (`StockPosition`) |

## Current behavior
- `GET /api/stock/` filtra por `search`, `warehouse_id`, `active`, `balance` (`inventory/api/stock_views.py:137-158`); filas sin clasificación ni usos (`:161-169`).
- `ProductForInventory` y `ProductInfo` no traen categoría ni usos (`catalog/services.py:54-61`, `inventory/application/movement_ports.py:7-14`).
- El detalle ofrece «Ver movimientos» y «Registrar apertura» (enlaza solo con `warehouse_id`); no ofrece ajuste; ningún flujo vuelve al detalle (`stock-opening.component.ts:258`, `adjustment-form.component.ts:225`); la lista no conserva filtros.

## Expected behavior
1. El listado muestra clasificación y usos de cada fila; el detalle los muestra junto a producto, estado, unidad, almacén y saldo.
2. Nuevos filtros combinables con los actuales: clasificación (cada categoría o «sin clasificar»), comprable (sí/no) y vendible (sí/no). Resultados siempre de la empresa de la sesión.
3. «Limpiar filtros» restablece todos; al volver del detalle se restauran filtros y página.
4. Detalle: «Registrar apertura» solo si `can_register_opening`; «Registrar ajuste» solo si el almacén está activo; si no procede, se oculta y se explica.
5. Ambos flujos abren con producto y almacén preseleccionados; guardar o cancelar vuelve al mismo detalle (saldo e historial recargados).

## Domain rules / invariants
- INV-01 (existente): saldo = Σ libro; no se altera. 
- INV-02 (existente): apertura solo sin movimientos previos, revalidada bajo bloqueo al confirmar (`RegisterOpening._reject_history`).
- INV-03 (existente): el ajuste conserva sus validaciones, permisos, idempotencia y concurrencia.
- INV-04 (nueva, solo lectura): `can_register_adjustment = warehouse_active`.
- INV-05 (nueva): Inventario no cambia categoría ni usos; los lee de Catálogo.

## Acceptance criteria
- AC-01: la consulta original (filtros actuales, paginación, «Ver movimientos») sigue funcionando y no altera saldos ni documentos.
- AC-02: filtros `category` (incl. `none`), `can_buy`, `can_sell` se combinan entre sí y con los actuales; ejemplos: intermedios no vendibles, empaques comprables, comprables y vendibles; solo productos de la empresa.
- AC-03: clasificación y usos proceden de Catálogo; no hay datos ni migraciones nuevas en Inventario.
- AC-04: apertura inelegible (con movimientos): acción oculta con nota; la API rechaza con 409 aunque se abra por URL, y la revalidación ocurre al confirmar.
- AC-05: apertura y ajuste reutilizan formularios y endpoints existentes, sin duplicarlos; producto y almacén preseleccionados.
- AC-06: tras guardar con éxito se vuelve al detalle con saldo e historial actualizados; cancelar vuelve sin cambios; un rechazo no deja cambios parciales y conserva los datos con el error por campo o de servicio.
- AC-07: la lista distingue cargando, vacío inicial, sin resultados con filtros y error con «Reintentar»; usable en móvil y escritorio.
- AC-08: los filtros y la página se conservan al volver del detalle.

## Edge cases / Error cases
- EDGE-01: producto sin clasificar (`category null`) → «Sin clasificar»; solo aparece con filtro «Sin clasificar» o sin filtro de clasificación.
- EDGE-02: producto sin usos → «Sin usos»; coincide con `can_buy=false` y `can_sell=false`.
- EDGE-03: parámetro inválido (`category`, `can_buy`, `can_sell`) → 400 por parámetro.
- EDGE-04: la apertura pasa a no elegible entre abrir la pantalla y confirmar → 409 `stock_history_exists`, el formulario conserva los datos y marca la línea.
- EDGE-05: `return`/ids inválidos en la URL → los formularios ignoran el retorno y usan el destino actual.
- EDGE-06: almacén inactivo → sin «Registrar ajuste» (con nota); apertura sigue su regla.

## Authorization / permissions
Sin permisos nuevos: `CompanyAdminPermission` y gate `inventory` existentes; la ocultación de acciones en el frontend es solo UX.

## API contract
- API-01: `GET /api/stock/` acepta `category` (`raw_material|packaging|intermediate|finished|merchandise|none`), `can_buy`, `can_sell` (`true|false`); 400 por parámetro inválido. Compatible hacia atrás (todos opcionales).
- API-02: cada fila de `GET /api/stock/` y el detalle `GET /api/stock/<product_id>/<warehouse_id>/` añaden `category` (string|null), `can_buy`, `can_sell`; el detalle añade `can_register_adjustment`. Cambio aditivo.

## UI behavior
Ver DDR. UI-01: lista (columnas, filtros, «Limpiar filtros», estados, estado conservado). UI-02: detalle (filas, acciones, notas). UI-03: apertura/ajuste con preselección y retorno (`return=stock`). Plantillas: «Lista de solo lectura con filtros» y «Detalle con historial embebido» (`design-system.md` §5).

## Non-functional requirements
Sin consultas adicionales por fila (categoría y usos viajan en el mismo DTO); móvil 375 px sin desborde; accesibilidad: etiquetas en filtros, texto además de color.

## Out of scope
Cambiar PB-INV-005, movimientos libres, compras/producción, costeo, reservas, devoluciones, exportaciones; editar clasificación o usos desde Inventario.

## Open questions
Ninguna bloqueante. Decisión tomada: los productos sin clasificar se pueden filtrar con la opción «Sin clasificar».

# Test Specification

## Unit / Integration tests (backend, `inventory/tests/test_stock_query.py` y `catalog/tests/test_services.py`)
- `list_products_for_inventory` devuelve `category`, `can_buy`, `can_sell`; aislamiento por empresa.
- `ListStock`/API: filtro por categoría, `none`, `can_buy`, `can_sell` y combinaciones con `search`/`balance`/`active`; 400 por valores inválidos.
- Detalle: `category`, usos y `can_register_adjustment` (almacén activo/inactivo).
- Apertura con historial por API → 409 (regresión) y flujo `RegisterOpening` sin cambios.

## Frontend (Karma)
- `stock-api.service`: parámetros y mapeo nuevos.
- `stock-list`: columnas, filtros combinados, «Limpiar filtros», restauración de estado, estados vacío/sin resultados/error.
- `stock-detail`: filas, visibilidad de acciones y notas, enlaces con `return=stock`.
- `stock-opening` / `adjustment-form`: preselección, retorno al detalle al guardar y cancelar, ignorar retorno inválido.

## E2E
**NO** — el flujo se cubre con integración backend y specs de componentes; no hay flujo crítico nuevo de punta a punta que justifique instalar Playwright.

## Regression tests
Suites existentes de `inventory`, `catalog` y `features/inventory` verdes.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | Regresión backend `test_stock_query`/`test_stock`; specs existentes de lista/detalle |
| AC-02 | Backend `test_stock_query` (filtros y combinaciones); spec `stock-list` |
| AC-03 | `test_services` (DTO desde Catálogo); revisión: sin migraciones en inventory (`makemigrations --check`) |
| AC-04 | Backend: 409 por API con historial; spec `stock-detail` (acción oculta + nota) |
| AC-05 | Specs `stock-opening`/`adjustment-form` (mismos endpoints, preselección) |
| AC-06 | Specs de retorno al guardar/cancelar; test backend de 409 sin cambios parciales (existente) |
| AC-07 | Spec `stock-list` (estados); revisión visual 375 px y escritorio |
| AC-08 | Spec `stock-list` + `StockFiltersState` |

# Implementation Plan

## Architecture considerations
Dependencia existente Inventory → Catalog por `services.py`; sin acoplamientos nuevos. Filtros nuevos se aplican en memoria sobre la composición actual (misma deuda técnica que PB-INV-005); la clasificación y usos se filtran en `list_products_for_inventory` (en BD).

## Proposed solution
Extender DTO/puerto/adaptador con `category`, `can_buy`, `can_sell`; añadir los filtros a `StockQuery` y a `_stock_query`; exponer campos y `can_register_adjustment`. En frontend, ampliar modelos/servicio/lista/detalle, añadir `StockFiltersState` y soporte de `product_id` + `return=stock` en apertura y ajuste.

## Files/components affected
- Backend: `catalog/services.py`; `inventory/application/movement_ports.py`, `application/stock_use_cases.py`, `infrastructure/adapters.py`, `api/stock_views.py`, `api/stock_serializers.py`; tests.
- Frontend (`features/inventory`): `models/stock.ts`, `services/stock-api.service.ts`, nuevo `services/stock-filters-state.ts`, `pages/stock-list/*`, `pages/stock-detail/*`, `pages/stock-opening/*`, `pages/adjustment-form/*`, specs y fixtures.
- Docs: `design-system.md` (línea de filtros conservados), `modulos-implementados.md`.
- Migraciones: ninguna.

## Implementation steps
1. Catálogo: `ProductForInventory` + `list_products_for_inventory(category, can_buy, can_sell)` (INV-05, AC-02, AC-03).
2. Inventario backend: `ProductInfo`, puerto, adaptador, `StockQuery`, `ListStock`, `_stock_query` y serializers (`API-01/02`, EDGE-03, INV-04).
3. Pruebas backend (AC-01..04, EDGE-01..03).
4. Frontend modelos/servicio y `StockFiltersState` (AC-08).
5. Lista: columnas, filtros, «Limpiar filtros», estados (UI-01, AC-07).
6. Detalle: filas, acciones y notas (UI-02, AC-04).
7. Apertura y ajuste: preselección y retorno (UI-03, AC-05, AC-06, EDGE-05).
8. Specs frontend, lint, build; docs; revisión visual.

## Database / migrations
Ninguna.

## Risks
- Composición en memoria productos × almacenes con más filtros (deuda anotada en PB-INV-005).
- La apertura es un formulario de varias líneas: la preselección ocupa la primera línea; si el almacén/producto no son elegibles, el formulario ya marca la línea por `OpeningCheckView`.
- Estado de filtros en memoria se pierde al recargar (aceptado en DDR).

## New dependencies
Ninguna.
