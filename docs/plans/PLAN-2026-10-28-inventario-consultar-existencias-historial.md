# PLAN-2026-10-28-inventario-consultar-existencias-historial (v1)

**Task:** TASK-inventario-consultar-existencias-historial · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-inventario-consultar-existencias-historial-existencias-y-detalle · Ninguno (NEEDS_PLAN)

## Objective
Consultar el saldo actual por producto y almacén (con búsqueda y filtros), ver el detalle con su historial y llegar al documento de origen, sobre el libro de movimientos existente.

## Context
Ver TASK. Decisión del usuario: «Registrar ajuste» fuera de alcance. Supuestos revisables en el TASK (filas = productos con control de stock × almacenes; estado por defecto Activos).

# Specification

## Domain context
`inventory` (saldos y movimientos); `catalog` (productos, solo por `catalog.services`).

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Existencia / saldo | Σ entradas − Σ salidas del libro por producto y almacén, en unidad base | PB-INV-004/005 |
| Estado de saldo | `zero` (= 0), `positive` (> 0), `negative` (< 0) | PB-INV-005 |
| Par | Producto + almacén | PB-INV-005 |

## Current behavior
Ver TASK (`stock_views.py:StockListView`, `stock-list.component.ts`).

## Expected behavior
`GET /api/stock/` lista todos los pares producto (con control de stock) × almacén con saldo, filtrable; hay un detalle por par; la UI ofrece lista, detalle e historial.

## Domain rules / invariants
- INV-01 El saldo mostrado = `get_balance` del libro (misma fuente); un par sin movimientos tiene saldo 0.
- INV-02 Solo productos que controlan stock; productos inactivos se incluyen únicamente si el filtro de estado lo permite, y conservan su historial.
- INV-03 Todo se limita a `company_id` de la sesión; ids ajenos ⇒ 404.
- INV-04 Estado de saldo derivado de la cantidad (nunca almacenado); cantidades como `Decimal`, serializadas como texto.
- INV-05 «Registrar apertura» solo se ofrece si producto y almacén están activos y el par no tiene movimientos (`has_history` del par); el backend de apertura lo vuelve a exigir (existente).

## Acceptance criteria
- AC-01 La lista muestra producto, almacén, unidad base y saldo actual; incluye pares sin movimientos con saldo 0.
- AC-02 Búsqueda por nombre (sin distinguir mayúsculas), filtro de almacén, de estado del producto (por defecto activos) y de saldo (cero / distinto de cero / negativo).
- AC-03 El saldo negativo se muestra con texto «Negativo» además del color; no aparecen «disponible», «reservado» ni valoración.
- AC-04 El detalle muestra nombre, unidad, almacén, saldo actual y el historial filtrado al par (más reciente primero, paginado), con el origen identificable y enlace al movimiento; productos inactivos se pueden abrir.
- AC-05 Acciones del detalle: «Ver movimientos» (lista prefiltrada por producto y almacén; filtros por fecha/tipo en esa lista) y «Registrar apertura» solo si cumple INV-05; sin «Registrar ajuste».
- AC-06 El historial de movimientos filtra por producto, almacén, fecha y tipo e identifica el documento de origen (existente en PB-INV-004; el selector de producto incluye siempre el producto prefiltrado y los inactivos).
- AC-07 Aislamiento por empresa: otra empresa no ve filas ni detalle (404).
- AC-08 El saldo de la lista y del detalle coincide con la suma del historial (entradas − salidas) del par.

## Edge cases / Error cases
- EDGE-01 Producto sin `tracks_stock` ⇒ no aparece en la lista; su detalle responde 404.
- EDGE-02 Almacén inactivo: aparece solo si se elige en el filtro; su detalle se abre; la apertura no se ofrece.
- EDGE-03 Parámetros inválidos (`warehouse_id`, `active`, `balance`) ⇒ 400 por parámetro.
- EDGE-04 Reversión: original «revertido» y contramovimiento netean a cero; el saldo no los cuenta doble.
- EDGE-05 Sin productos/almacenes ⇒ lista vacía (200).
- EDGE-06 Saldo negativo (posible con `allow_negative`) se lista y filtra como `negative`.

## Authorization / permissions
Administrador de la empresa (`CompanyAdminPermission`) y `required_modules = ('inventory',)`, como el resto de `/api/stock/`.

## API contract
- API-01 `GET /api/stock/` (cambio compatible: la forma de cada fila se amplía; se añaden filtros). Query: `search`, `warehouse_id` (UUID), `active` = `true|false|all` (por defecto `true`), `balance` = `zero|nonzero|negative`, `page`, `page_size`. Fila: `product_id`, `product_name`, `product_active`, `warehouse_id`, `warehouse_name`, `warehouse_active`, `quantity` (texto decimal), `balance_state` = `zero|positive|negative`, `unit{abbreviation, allows_fractions}|null`. Orden: nombre de producto, nombre de almacén. Sin `warehouse_id`, solo almacenes activos; con `warehouse_id`, ese almacén aunque esté inactivo.
- API-02 `GET /api/stock/<product_id>/<warehouse_id>/` ⇒ la misma forma de fila más `has_history` (bool) y `can_register_opening` (bool). 404 si el producto no controla stock / no existe / es de otra empresa, o el almacén no existe.
- El historial usa `GET /api/stock-movements/?product_id=&warehouse_id=&page_size=` (existente, PB-INV-004).

## UI behavior
- UI-01 Lista con buscador, filtros y columnas del DDR; estados cargando/vacío/error.
- UI-02 Detalle con `dl`, acciones y sección «Historial de movimientos» del DDR; ruta `inventory/stock/:productId/:warehouseId` con `moduleGuard`.
- UI-03 Saldo negativo con texto «Negativo» y color; filas de producto inactivo con badge «Inactivo».

## Non-functional requirements
`Decimal`; sin migraciones ni dependencias; composición en memoria acotada a productos con control de stock de la empresa × almacenes (volumen de MVP); textos en español.

## Out of scope
Registrar ajuste, reservas/disponible, valoración/costeo, kardex con saldo acumulado, exportar, transferencias.

## Open questions
Ninguna bloqueante.

# Test Specification

## Unit tests
Dominio/aplicación: estado de saldo (`zero/positive/negative`), composición de filas (par sin movimientos = 0, orden, filtros) con repositorios en memoria.

## Integration tests
API con BD: AC-01/02 (búsqueda, almacén, activo, saldo), EDGE-01..06, AC-07 (dos empresas), AC-08 (lista y detalle = `get_balance`), `can_register_opening`, 400 por parámetro, 403 sin módulo. `catalog.services.list_products_for_inventory` (empresa, `tracks_stock`, búsqueda, activo).
Frontend (Karma): servicio (parámetros y mapeo), `stock-list` (filtros, negativo con texto, inactivo), `stock-detail` (saldo 0 sin movimientos, acciones condicionadas, 404), `movement-list` (producto prefiltrado presente).

## E2E
**NO** — sin flujo crítico nuevo de punta a punta; cubierto por API y specs de componente.

## Regression tests
Suites de apertura (`OpeningApiTests`, `ConcurrentOpeningTests`), movimientos, fronteras (`test_boundaries`), specs de `stock-opening` y `stock-list` actualizados.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01, AC-02 | tests de API de lista + spec `stock-list` |
| AC-03 | spec `stock-list` y `stock-detail` (texto «Negativo», sin columnas prohibidas) |
| AC-04, AC-05 | tests API de detalle + spec `stock-detail` |
| AC-06 | tests existentes de filtros de movimientos + spec `movement-list` (selector con producto prefiltrado/inactivo) |
| AC-07 | test API con dos empresas |
| AC-08 | test API: saldo de lista/detalle = Σ del historial, incluida una reversión |

# Implementation Plan

## Architecture considerations
Sin ADR: no hay persistencia, permisos ni dependencia nuevos. El módulo `inventory` compone productos (vía puerto `ProductDirectory` → `catalog.services`) con saldos agregados del libro; el dominio no importa Django.

## Proposed solution
- `catalog.services.list_products_for_inventory(company_id, *, search, active)` → lista de `ProductForInventory` (se añade `active`) solo con `tracks_stock`, ordenada por nombre.
- Puerto `ProductDirectory.list_products(search, active)` + adaptador.
- Repositorio: `balances_by_pair()` (dict `(product_id, warehouse_id) → Decimal`, agregado `_signed_sum`) y `has_history_in(product_id, warehouse_id)`.
- Aplicación: `ListStock` recompone filas (productos × almacenes), aplica filtros de saldo/almacén, ordena; `GetStockPosition` para el detalle. `balance_state(quantity)` en dominio.
- API: `StockListView` ampliada y `StockDetailView` nueva; serializers.
- Frontend: `stock-list` con filtros; `stock-detail` nueva con historial (`MovementsApiService`); `movement-list`: incluir el producto prefiltrado en el selector (REV-09); design-system.

## Files/components affected
- Backend: `catalog/services.py`; `inventory/application/movement_ports.py`, `stock_use_cases.py`; `domain/stock.py`, `repositories.py`; `infrastructure/adapters.py`, `django/movement_repository.py`; `api/stock_views.py`, `stock_serializers.py`, `stock_urls.py`; tests (`inventory/tests`, `catalog/tests`).
- Frontend: `features/inventory/models/stock.ts`, `services/stock-api.service.ts` (+spec), `pages/stock-list`, `pages/stock-detail` (nueva), `pages/movement-list`, `app.routes.ts`.
- Docs: `docs/design/design-system.md`, `docs/architecture/ddd.md` (nota), `docs/producto/modulos-implementados.md`.

## Implementation steps
1. Catálogo: `list_products_for_inventory` + test (INV-02, INV-03).
2. Dominio y repositorio: `balance_state`, `balances_by_pair`, `has_history_in` + tests (INV-01, INV-04, EDGE-04).
3. Aplicación: `ListStock` (productos × almacenes, filtros) y `GetStockPosition` + tests (AC-01, AC-02, EDGE-01..06, INV-05).
4. API de lista y detalle con filtros/400 (API-01, API-02, AC-07, AC-08) + tests.
5. Frontend: modelos/servicio y `stock-list` (UI-01, UI-03, AC-01..03).
6. Frontend: `stock-detail`, ruta, historial y acciones (UI-02, AC-04, AC-05); REV-09 en `movement-list` (AC-06).
7. Docs y verificación completa (backend `manage.py test`, `makemigrations --check`, lint, build, Karma).

## Database / migrations
Ninguna.

## Risks
Composición en memoria con muchos productos × almacenes (mitigación: solo productos con control de stock y almacenes activos por defecto; paginar antes de serializar; migrar a consulta en BD si crece); cambio de forma de `GET /api/stock/` (único consumidor: pantalla Existencias); línea base de 71 specs rotos del frontend.

## New dependencies
Ninguna.
