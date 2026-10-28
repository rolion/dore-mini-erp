# PLAN-2026-10-28-inventario-movimientos-trazables (v1)

**Task:** TASK-inventario-movimientos-trazables · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-inventario-movimientos-trazables-lista-y-detalle-movimientos · ADR-inventario-movimientos-trazables-registro-idempotente-y-saldo

## Objective
Registrar entradas y salidas de stock como un libro inmutable con origen trazable, idempotente ante reintentos, del que se deriva el saldo, y consultarlo en Inventario → Movimientos (lista y detalle de solo lectura).

## Context
Ver TASK. Supuestos (no bloqueantes, revisables): los movimientos se crean desde otros módulos por la fachada `inventory.services` (sin endpoint HTTP de alta); «tipo» = Entrada/Salida; origen = clase de documento (`sales_order`, `purchase_receipt`, `inventory_adjustment`) o ninguno; las salidas sin saldo se rechazan salvo `allow_negative`; el saldo cuenta todas las filas del libro.

# Specification

## Domain context
`inventory` (propietario del movimiento); `catalog` (datos de producto/unidad por `catalog.services`); `shared` (puertos `stock_history`, `module_gate`).

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Movimiento | Registro inmutable de una entrada o salida de un producto en un almacén | PB-INV-004 |
| Tipo | Dirección: entrada (`in`) o salida (`out`) | PB-INV-004 |
| Origen | Documento fuente (clase + id + línea) que causó el movimiento | PB-INV-004 |
| Contramovimiento | Movimiento inverso que revierte a otro; el original pasa a «revertido» | PB-INV-004 |
| Saldo | Σ entradas − Σ salidas del libro por producto y almacén | PB-INV-004 |

## Current behavior
Sin movimientos ni saldos; `stock_history` y `WarehouseActivity` responden «no» (`shared/stock_history.py:25-31`, `inventory/infrastructure/activity.py:4-16`).

## Expected behavior
Existe el libro de movimientos; productores lo escriben por fachada; la UI lista y detalla; los puertos se conectan al libro.

## Domain rules / invariants
- INV-01 Un movimiento guarda empresa, producto, almacén, tipo, cantidad > 0, fecha, usuario y origen si existe.
- INV-02 Inmutable: sin edición ni borrado; solo `confirmed → reversed` al revertir.
- INV-03 Idempotencia: misma `(company, source_type, source_id, source_line, product, warehouse, kind)` ⇒ un solo movimiento; reintento devuelve el existente; con otra cantidad ⇒ conflicto.
- INV-04 Saldo = Σ entradas − Σ salidas del libro; se calcula, nunca se escribe.
- INV-05 Una salida sin saldo suficiente se rechaza salvo `allow_negative=True`; serializada por bloqueo del almacén.
- INV-06 Solo productos con `tracks_stock`, cantidad coherente con `allows_fractions`, almacén activo de la empresa.
- INV-07 Un movimiento se revierte una sola vez (contramovimiento opuesto, vinculado).
- INV-08 Todo con `company_id`; ids ajenos ⇒ 404.
- INV-09 Existe historial de un producto ⇒ `stock_history.has_history` verdadero; saldo ≠ 0 ⇒ `has_nonzero_balance` verdadero (existentes: puertos de PB-INV-001/002).

## Acceptance criteria
- AC-01 Cada movimiento persiste los campos de INV-01 (verificado por lectura de API/BD).
- AC-02 Saldo correcto tras entradas/salidas/reversiones; no hay endpoints ni métodos de edición/borrado (405 en API).
- AC-03 Reintentar la misma operación de origen (secuencial y concurrente) deja un solo movimiento visible.
- AC-04 Lista: columnas fecha/hora, referencia, producto, almacén, tipo, entrada, salida, unidad, origen; entradas y salidas en columnas separadas.
- AC-05 Filtros por rango de fechas, producto, almacén, tipo y origen.
- AC-06 Detalle: identificador, estado, empresa, producto, almacén, cantidad, tipo, fecha, usuario, referencia/motivo, origen y contramovimientos; permite reconstruir la operación.
- AC-07 El enlace al origen aparece solo si el módulo propietario está habilitado y existe pantalla.
- AC-08 Sin acciones Editar/Eliminar en UI; menú «Movimientos» bajo Inventario.
- AC-09 Primer movimiento de un producto bloquea cambiar `tracks_stock`/unidad (409 `stock_history_locked`); un almacén con saldo ≠ 0 no se desactiva (409 `warehouse_has_stock`).

## Edge cases / Error cases
- EDGE-01 Dos peticiones simultáneas con el mismo origen ⇒ una crea, otra recibe el existente.
- EDGE-02 Cantidad ≤ 0, fraccionaria en unidad entera, producto sin `tracks_stock`, almacén inactivo/ajeno ⇒ error de validación (`MovementValidationError`).
- EDGE-03 Revertir dos veces ⇒ conflicto `already_reversed`.
- EDGE-04 Salidas simultáneas que exceden el saldo ⇒ solo pasan las que caben.
- EDGE-05 Filtros inválidos (fecha, UUID, tipo, origen, rango invertido) ⇒ 400 por parámetro.

## Authorization / permissions
Administrador de la empresa (`CompanyAdminPermission`); `required_modules = ('inventory',)`. La fachada recibe `company_id` explícito.

## API contract
- API-01 `GET /api/stock-movements/` (paginada como almacenes; filtros `date_from`, `date_to`, `product_id`, `warehouse_id`, `kind` = `in|out`, `source_type` = clase o `none`). Ítem: `id`, `occurred_at`, `reference`, `product{id,name}`, `warehouse{id,name}`, `kind`, `quantity_in`, `quantity_out` (string decimal o `null`), `unit{abbreviation}`, `status`, `source{type,label,id,reference,available}|null`.
- API-02 `GET /api/stock-movements/<uuid>/`: lo anterior más `quantity`, `reason`, `user{id,name}`, `reversed_by{id}|null`, `reverses{id}|null`, `created_at`.
- API-03 Otros métodos ⇒ 405. Errores: 400 por parámetro, 403, 404.
- Facade Python (no HTTP): `record_movement(company_id, *, product_id, warehouse_id, kind, quantity, user_id, user_name, reference='', reason='', source=None, occurred_at=None, allow_negative=False) -> (MovementDTO, created)`, `reverse_movement(company_id, movement_id, *, user_id, user_name, reason='')`, `get_balance(company_id, product_id, warehouse_id)`.

## UI behavior
- UI-01 Lista según DDR (filtros, columnas separadas, badge de tipo, «Revertido», paginación servidor; estados cargando/vacío/error).
- UI-02 Detalle según DDR con enlace condicionado al origen y a contramovimientos.
- UI-03 Entrada «Movimientos» en el submenú Inventario y rutas `inventory/movements[/:id]` con `moduleGuard`.

## Non-functional requirements
`Decimal` siempre; textos en español (+ claves i18n es/en/de del menú); lista con índices `(company_id, occurred_at)` y `(company_id, product_id, warehouse_id)`; sin dependencias nuevas.

## Out of scope
Productores reales (ventas, compras, ajustes), recepciones, endpoint de alta manual, pantalla de saldos/existencias, costos y valorización, transferencias, regularización.

## Open questions
Política definitiva de saldo negativo para ventas (decide la historia de ventas con inventario).

# Test Specification

## Unit tests
Dominio: `StockMovement` (INV-01, 02, 07), catálogo de `SourceType`.

## Integration tests
Fachada con BD: idempotencia secuencial y concurrente (AC-03, EDGE-01), saldo (AC-02), rechazo de salida (INV-05, EDGE-04), validaciones (INV-06, EDGE-02), reversión (INV-07, EDGE-03). API: lista/detalle, filtros, 400/403/404/405, aislamiento (INV-08), `available` según módulo (AC-07). Puertos: historial bloquea producto (AC-09), saldo bloquea almacén (AC-09). `test_boundaries` con `inventory: {'catalog'}`. Migración. Frontend (Karma): servicio, lista, detalle, ruta/menú.

## E2E
**NO** — no hay flujo crítico de punta a punta nuevo; la lista es de solo lectura y se cubre con specs de componente y pruebas de API.

## Regression tests
Suites de catálogo, inventario (almacenes), modularity y fronteras.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | test fachada + API detalle |
| AC-02 | tests de saldo y 405 en API |
| AC-03 | test de idempotencia secuencial y concurrente (hilos, BD) |
| AC-04, AC-06, AC-08 | specs de lista y detalle |
| AC-05 | tests de filtros de API + spec de lista |
| AC-07 | test de API con módulo de origen on/off + spec de detalle |
| AC-09 | tests de puertos con BD real |

# Implementation Plan

## Architecture considerations
Ver ADR: libro append-only, restricción única parcial, bloqueo de almacén, fachada `inventory.services`, consumo de `catalog.services` por adaptador, registro de puertos en `ready()`.

## Proposed solution
Dominio puro (`movement.py`, `SourceType`), puerto `ProductDirectory` (catálogo) y caso de uso `RecordMovement`/`ReverseMovement`/consultas, repositorio Django `DjangoStockMovementRepository(company_id)`, vistas de solo lectura, frontend lista/detalle en `features/inventory`.

## Files/components affected
- Backend: `catalog/services.py` (+`get_products_for_inventory`); `inventory/domain/movement.py`, `exceptions.py`, `repositories.py`; `application/ports.py`, `movement_use_cases.py`; `infrastructure/django/models.py`, `movement_repository.py`, `infrastructure/adapters.py`, `activity.py`; `inventory/services.py`; `api/movement_*.py`, `api/urls` y `config/urls.py`; `apps.py`; migración `inventory/0002`; `sales/tests/test_boundaries.py`; tests; `docs/architecture/ddd.md`.
- Frontend: `features/inventory` (modelos, servicio, `movement-list`, `movement-detail`), `app.routes.ts`, `routes.json`, i18n es/en/de, `docs/design/design-system.md`.

## Implementation steps
1. Catalog: `get_products_for_inventory` + test.
2. Dominio de movimiento y excepciones (INV-01, 02, 07).
3. Modelo + migración `0002` (INV-03 restricciones, índices).
4. Repositorio, adaptador de catálogo, casos de uso y fachada `services.py` (INV-03..07, AC-01..03).
5. Puertos: proveedor de historial en `ready()` y `WarehouseActivity` real (INV-09, AC-09); actualizar test de fronteras.
6. API de lectura con filtros y `available` (AC-04..07).
7. Frontend lista y detalle, ruta y menú (UI-01..03, AC-08).
8. Docs (`ddd.md`, `design-system.md`) y verificación completa.

## Database / migrations
`inventory/0002`: `CreateModel StockMovement` (`inventory_stock_movement`) con `UniqueConstraint` parcial de idempotencia (condición `source_type` no nulo), `unique(reverses)` parcial, `CheckConstraint quantity > 0`, índices. No toca migraciones existentes.

## Risks
Bloqueos de `stock_history` activos con el primer movimiento (esperado); concurrencia en PostgreSQL (tests requieren BD real, `TransactionTestCase`); suposición de salida sin saldo; línea base de specs rotos del frontend.

## New dependencies
Ninguna.
