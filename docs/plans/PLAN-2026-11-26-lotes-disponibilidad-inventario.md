# PLAN-2026-11-26-lotes-disponibilidad-inventario (v1)

**Task:** TASK-lotes-disponibilidad-inventario · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-lotes-disponibilidad-inventario-pantalla-lotes · ADR-lotes-disponibilidad-inventario-modelo-lotes

## Objective
Inventario identifica por lote los cuñapés a granel y distingue stock **físico** de **disponible para empaque** (solo lotes liberados), bloqueando el granel en refrigeración para empaque y salidas, sin alterar los productos sin lotes. Se reutilizan y extienden las funciones existentes; no se crean duplicadas.

## Context
Ver TASK. Tarjeta Trello DORE-PROD-002; contrato que consumirán PROD-004..008.

# Specification

## Domain context
Bounded context **Inventory** (libro de movimientos). Relacionados solo por fachada: `accounting` (período fiscal), `catalog` (producto). Producción (futuro) consume la fachada.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Lote | Tanda de un producto a granel en un almacén, con código `L-YYYYMMDD-NNNN` | Trello PROD-002 / usuario |
| Físico (del lote) | Suma con signo de los movimientos del lote | Trello |
| Disponible para empaque | Físico si el lote está liberado; 0 si está en refrigeración | Trello |
| Estado del lote | `refrigerating` (En refrigeración) · `released` (Liberado) | Trello |
| Stock sin lote | Físico del producto/almacén − suma de saldos de sus lotes | ADR |

## Current behavior
Sin lotes: el saldo es la suma de movimientos por producto+almacén (`movement_repository.py:122-126`), y toda salida con saldo suficiente se acepta (`movement_use_cases.py:73-81,140-155`).

## Expected behavior
Un producto puede tener lotes. Consultar lotes muestra producto, almacén, lote, físico, disponible y estado. Con 118 en refrigeración: 118 físicos, 0 disponibles. Las salidas con lote solo se aceptan con lote liberado y saldo; las salidas sin lote solo consumen stock sin lote. Los productos sin lotes se comportan como hoy.

## Domain rules / invariants
- INV-01 (nueva): el saldo de un lote nunca es negativo, ni con la política de stock negativo.
- INV-02 (nueva): una salida con lote exige lote liberado y saldo suficiente.
- INV-03 (nueva): una salida sin lote solo consume stock sin lote (con política negativa, ese remanente puede quedar negativo; los lotes no).
- INV-04 (nueva): la entrada a un lote solo ocurre al crearlo (`create_lot`).
- INV-05 (nueva): la reversión hereda el lote, no exige liberado, sí saldo del lote ≥ cantidad.
- INV-06 (nueva): liberar es idempotente; solo `refrigerating → released`; no hay vuelta atrás.
- INV-07 (nueva): código `L-YYYYMMDD-NNNN`, `YYYYMMDD` = fecha local del lote, número correlativo por empresa y período fiscal, sin duplicados ni huecos por fallos (se asigna en la transacción).
- INV-08 (existente): aislamiento por `company_id`; movimientos serializados por el bloqueo del almacén.
- INV-09 (nueva): un lote pertenece a un solo producto y almacén; sus movimientos deben coincidir con ellos.

## Acceptance criteria
- AC-01: `create_lot` crea el lote en refrigeración y su entrada (cantidad > 0, validaciones de producto existentes: controla stock, fracciones) en una transacción; devuelve código, estado y movimiento.
- AC-02: `create_lot` es idempotente por origen (`source_type`/`source_id`): repetir devuelve el mismo lote sin duplicar movimientos ni gastar número; con otra cantidad → 409 `source_operation_mismatch`.
- AC-03: el código sigue `L-YYYYMMDD-NNNN`; el número reinicia por período fiscal y no se repite dentro de él (también bajo concurrencia, PostgreSQL).
- AC-04: sin período fiscal abierto para la fecha, `create_lot` falla con `fiscal_period_missing`/`fiscal_period_closed` sin crear nada.
- AC-05: con un lote en refrigeración de 118: físico 118, disponible 0, estado En refrigeración.
- AC-06: `release_lot` pasa a Liberado, registra quién y cuándo; el físico no cambia y el disponible pasa a 118; repetirlo no cambia nada ni crea movimientos.
- AC-07: una salida con lote en refrigeración se rechaza; con lote liberado se acepta hasta su saldo; más allá, `InsufficientStock` con el disponible del lote; nunca deja el lote negativo (con o sin política negativa).
- AC-08: una salida sin lote no puede consumir unidades de ningún lote (ejemplo 118/60/22: pedir 30 sin lote → rechazado, disponible 22).
- AC-09: ventas, ajustes y reversiones usan la misma regla (salida sin lote) y siguen idempotentes; los errores de saldo insuficiente del API mantienen su formato.
- AC-10: la reversión de la entrada de un lote hereda el lote y respeta INV-05; la reversión de una salida con lote devuelve las unidades a ese lote.
- AC-11: `GET /api/stock-lots/` lista lotes de la empresa (paginado) con filtros `search`, `product_id`, `warehouse_id`, `status`, `with_stock`; devuelve producto, unidad, almacén, código, estado, `physical_quantity`, `available_quantity`, fechas y liberación; `GET /api/stock-lots/<id>/` el detalle; otra empresa → 404.
- AC-12: productos sin lotes: respuestas y reglas de Existencias, movimientos, ventas y compras no cambian (solo se añade `has_lots=false`).
- AC-13: Existencias (lista y detalle) devuelven `has_lots`; el movimiento devuelve `lot_id`/`lot_code` (nulos si no tiene).
- AC-14: Frontend: pantalla Inventario › Lotes (lista con filtros, estados, badge, físico/disponible), sección «Lotes» en el detalle de existencia, fila «Lote» en el detalle de movimiento y entrada de menú; es/en/pt completos.
- AC-15: con Producción sin lotes, nada cambia (no hay dependencia del módulo Producción).

## Edge cases / Error cases
- Cantidad ≤ 0, con fracciones en unidad entera, producto sin control de stock, almacén inactivo/inexistente: mismos errores que `RecordMovement`.
- Salida con lote de otro producto/almacén o de otra empresa: 400/404 sin revelar datos.
- Liberar un lote inexistente: 404 de dominio; ya liberado: éxito sin cambios.
- Dos salidas simultáneas del mismo lote o dos `create_lot` simultáneos: solo se cumplen las que caben / numeración sin duplicados.
- Ajuste que excede el stock sin lote de un producto con lotes: rechazado con el disponible sin lote.
- Reversión de entrada de lote ya parcialmente consumido: rechazada por INV-05.

## Authorization / permissions
Lecturas bajo `required_modules=('inventory',)` y la autenticación/empresa del resto de Existencias. Crear/liberar solo por fachada (código de otros módulos), sin endpoints. El frontend no es barrera.

## API contract
- API-01 `GET /api/stock-lots/` y API-02 `GET /api/stock-lots/<uuid>/` (solo lectura). Cantidades como `DecimalField(16,4)`.
- API-03 aditivos: `has_lots` en Existencias; `lot_id`, `lot_code` en movimientos. Sin cambios incompatibles.
- Errores 409 de numeración: `{code, detail, period?}`.

## UI behavior
Según DDR: UI-01 lista Lotes (plantilla lista de solo lectura con filtros, variante compacta < 992 px); UI-02 sección Lotes en `stock-detail`; UI-03 fila Lote en `movement-detail`; UI-04 menú. Estados cargando/vacío/error/éxito; badge de estado; sin acciones.

## Non-functional requirements
Consultas de lotes sin N+1 (saldos agregados en una consulta); migración aditiva; textos i18n es/en/pt; sin `any`.

## Out of scope
Crear/liberar lotes por pantalla o API; mínimo de horas de refrigeración (PROD-005); órdenes, recetas, empaque (PROD-003..008); ajuste por lote; costeo por lote; venta eligiendo lote.

## Open questions
- Interpretación del código `L-YYYYMMDD-0001` (fecha del lote + correlativo por período fiscal), a confirmar en la revisión del PR; cambiarla afecta solo `LotCode` y su prueba.

# Test Specification

## Unit tests
Dominio: `StockLot` (creación, `release` idempotente, código y formato), reglas INV-01..05 como funciones puras de saldo consumible.

## Integration tests
Casos de uso con base PostgreSQL de pruebas: `CreateLot`, `ReleaseLot`, `RecordMovement/RecordOutputs/ReverseMovement/ReverseSourceMovements` con y sin lote, política negativa, `ListLots`; numeración y salidas concurrentes con hilos y comprobación por mutación (como `test_order_numbering_concurrency.py`); API de lotes y de existencias/movimientos (respuestas aditivas); aislamiento por empresa.

## E2E
**NO** — no es un flujo crítico de punta a punta todavía (no hay alta de lotes por pantalla); cubierto por integración y Karma.

## Regression tests
Suites existentes de `inventory/tests`, `sales`, `purchases`, `costing` y `data_import` en verde sin modificar sus expectativas (AC-09, AC-12).

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01, 02 | Integración `CreateLot` + fachada |
| AC-03, 04 | Integración + concurrencia PostgreSQL |
| AC-05, 06 | Unit dominio + integración `ListLots`/`ReleaseLot` |
| AC-07, 08 | Integración movimientos con lote/sin lote, con y sin política negativa; concurrencia |
| AC-09, 12, 15 | Regresión de suites existentes + prueba específica de ajuste y venta con lotes |
| AC-10 | Integración reversiones |
| AC-11, 13 | Pruebas de API (filtros, paginación, empresa, aditivos) |
| AC-14 | Karma de lista, detalle y servicio; `npm run lint`, `i18n:check` y prueba de claves es/en/pt |

# Implementation Plan

## Architecture considerations
Ver ADR. Se extiende `RecordMovement`/`RecordOutputs`/reversiones con un único método de repositorio de saldo consumible; no se crea otro registrador de movimientos ni otra consulta de existencias.

## Proposed solution
Lote como dimensión nullable del libro; agregado `StockLot` con `release()`; repositorio de lotes; casos de uso `CreateLot`, `ReleaseLot`, `ListLots`; fachada ampliada; endpoints de lectura; helper de numeración en `shared/`.

## Files/components affected
- Backend `inventory`: `domain/lot.py` (nuevo), `domain/movement.py` (+`lot_id`, `SOURCE_TYPES`), `domain/exceptions.py`, `domain/repositories.py`, `application/movement_use_cases.py` (extender), `application/lot_use_cases.py` (nuevo), `application/stock_use_cases.py` (`has_lots`), `infrastructure/django/models.py` (+`StockLotModel`, `LotNumberCounterModel`, `StockMovementModel.lot`), `movement_repository.py` (saldo consumible, lote en insert/entidad), `lot_repository.py` (nuevo), `api/lot_views.py`/`lot_serializers.py`/`lot_urls.py` (nuevos), `api/stock_*`/`movement_*` (campos aditivos), `services.py` (fachada), migración `0004`.
- `backend/shared/fiscal_numbering.py` (nuevo) y, en el último paso, adaptadores de numeración de `sales` y `purchases`.
- Frontend `features/inventory`: `models/lot.ts`, `services/lots-api.service.ts`, `pages/lot-list`, sección en `stock-detail`, fila en `movement-detail`, `app.routes.ts`, menú, `assets/i18n/{es,en,pt}.json`.
- Tests: backend (`inventory/tests/test_lots*.py`, concurrencia, API) y Karma. Docs: TASK/PLAN/ADR/DDR.

## Implementation steps
1. Migración `0004` y modelos de lote/contador/columna `lot` (INV-07, INV-09).
2. Helper `shared/fiscal_numbering.py` + prueba (AC-03).
3. Dominio `StockLot`, `LotCode`, excepciones; `lot_id` en `StockMovement` y `production_order` en `SOURCE_TYPES` (INV-04, INV-06).
4. Repositorio: `consumable_balance`, lote en insert/lectura, saldos por lote, repositorio de lotes.
5. Extender `RecordMovement`/`RecordOutputs`/reversiones al saldo consumible; verificar suites existentes en verde (INV-01..03, 05; AC-07..10, 12).
6. `CreateLot`/`ReleaseLot`/`ListLots` y fachada (`create_lot`, `release_lot`, `get_lot(s)`, `record_movement(lot_id=)`) (AC-01, 02, 04..06).
7. API de lotes y campos aditivos en existencias/movimientos (AC-11, 13).
8. Pruebas de concurrencia PostgreSQL con mutación (AC-03, 07).
9. Frontend: modelos, servicio, lista de lotes, sección en detalle de existencia, fila en movimiento, ruta, menú, i18n es/en/pt, specs (AC-14).
10. Paso aislado (commit propio, diferible): migrar `OrderNumberingAdapter` y `PurchaseNumberingAdapter` al helper; sus pruebas de carrera existentes en verde.

## Database / migrations
`inventory/0004_stock_lots`: crea `inventory_stock_lot`, `inventory_lot_number_counter` y `inventory_stock_movement.lot_id` (nulo) con índices; sin migrar datos; depende de la última de inventory. Nunca se edita una migración aplicada.

## Risks
Regresión en los controles de saldo (mitigado por suites existentes y paso 5 como puerta); carreras (pruebas con hilos y mutación); dependencia de período fiscal; paso 10 toca código en producción (aislado y diferible).

## New dependencies
Ninguna.
