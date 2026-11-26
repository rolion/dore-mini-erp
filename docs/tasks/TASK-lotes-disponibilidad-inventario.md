# TASK-lotes-disponibilidad-inventario: Disponibilidad de cuñapés por lote en Inventario

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-lotes-disponibilidad-inventario (base: `produccion`)
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/128
**Fuente:** https://trello.com/c/12PuWhBD/2-dore-prod-002-controlar-disponibilidad-de-cu%C3%B1ap%C3%A9s-por-lote-en-inventario

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-26 | (nuevo) → INVESTIGATION | Task creado desde Trello DORE-PROD-002 | delivery-start |
| 2026-11-26 | INVESTIGATION → DESIGN | NEEDS_ARCHITECTURE, diseño requerido | delivery-start |
| 2026-11-26 | DESIGN → ARCHITECTURE | DDR escrito | delivery-start |
| 2026-11-26 | ARCHITECTURE → PLANNING | ADR escrito | delivery-start |
| 2026-11-26 | PLANNING → ENGINEERING | PLAN v1 READY (decisiones de negocio respondidas por el usuario) | delivery-start |
| 2026-11-26 | ENGINEERING → REVIEW | Implementación y pruebas escritas; suites de inventory, sales, purchases, costing, data_import y shared (1218) y Karma de inventory/layout/i18n (237) en verde por verificación propia | delivery-build |

## Investigación

### Requerimiento
Tarjeta Trello **DORE-PROD-002 · Controlar disponibilidad de cuñapés por lote en Inventario** (insumo, no Specification aprobada). Historia: como responsable de almacén, distinguir stock físico del disponible para empacar. Ampliar Inventario para identificar por lote los cuñapés a granel de producción: el saldo físico incluye lotes refrigerándose y liberados; el disponible para empaque solo las unidades restantes de lotes liberados.

Comportamiento esperado de la tarjeta:
- Inventario permite consultar producto, almacén, lote, cantidad física, cantidad disponible para empaque y estado del lote.
- Con 118 cuñapés en refrigeración: 118 físicos y 0 disponibles.
- El granel en refrigeración queda bloqueado para empaque y venta; los lotes liberados abastecen empaque; las presentaciones terminadas siguen el flujo de ventas existente.
- La consulta conserva visibilidad y comportamiento de productos sin lotes.
- Sin dependencias; reutiliza Catálogo e Inventario.

Contexto del tablero «produccion dore» (solo lectura, para encajar la interfaz): PROD-004 crea el lote al pasar a refrigeración (movimientos con lote, idempotente); PROD-005 lo libera; PROD-007/008 empacan consumiendo lotes liberados (uno o varios, con detalle por lote).

Aclaraciones del usuario (chat): usar la rama `produccion`; revisar lo ya implementado en Inventario y no duplicar funciones; **salida sin lote** → solo consume stock sin lote (respuesta a la pregunta con ejemplo 118/60/22); **lotes**: solo capacidad en Inventario (fachada + consulta; sin pantalla de alta/liberación manual); **código de lote** `L-YYYYMMDD-0001`, correlativo al período fiscal; con el módulo de Producción deshabilitado no hay lotes, así que la regla no interviene.

### Hechos encontrados
- `origin/produccion` == `HEAD` (`0d05db92`); los PR de Producción usan `produccion` como base (PR #127, recetas). El módulo `backend/modules/production` aún no existe en esta rama (solo en la rama de PROD-001).
- **No existe ningún concepto de lote en Inventario**: `grep` de «lote/batch/lot» en `backend/modules/inventory` solo toca `domain/exceptions.py` (texto no relacionado).
- Existencias = suma con signo del libro: `StockMovementModel` (`inventory/infrastructure/django/models.py:28-62`, sin lote); `balance()`, `balances_for()`, `list_balances()` (`movement_repository.py:122-126,153-158,189-199`) agrupan por producto+almacén con `_signed_sum()` (`:79-82`).
- Control de saldo para salidas bajo bloqueo del almacén: `RecordMovement._check_balance` (`application/movement_use_cases.py:73-81`), `RecordOutputs._check_balances` (`:140-155`), `ReverseMovement` (`:171-177`), `ReverseSourceMovements._check_balances` (`:221-241`); todos usan `repository.balance(s)` y la política `InventoryPolicy.allow_negative_stock`.
- Idempotencia por origen `(source_type, source_id, source_line, producto, almacén, tipo)` con restricción única (`models.py:56-59`); `SOURCE_TYPES` cerrado en `domain/movement.py:36-44` (no incluye producción).
- Existencias: `ListStock`/`GetStockPosition` (`application/stock_use_cases.py:152-226`), vistas `StockListView`/`StockDetailView` (`api/stock_views.py:150-197`), serializers (`api/stock_serializers.py`).
- Fachada pública `inventory/services.py` (`record_movement`, `reverse_*`, `get_balance`, `record_outputs`, `get_balances`, `get_company_stock`…): los demás módulos solo entran por ahí; `costing`, `sales`, `purchases` y `data_import` la consumen.
- Numeración por período fiscal ya implementada **dos veces** con la misma forma: `sales/infrastructure/adapters.py:492-520` y `purchases/infrastructure/adapters.py:167-195` (`accounting_services.lock_open_period` + contador `select_for_update`). El ADR de compras (`docs/adr/ADR-numeracion-correlativa-compras-contador-por-periodo.md`, decisión 8) dice «se revisa cuando aparezca un tercer consumidor»: los lotes lo son.
- Frontend: `features/inventory` tiene `stock-list`, `stock-detail` (plantilla «Detalle con historial embebido»), `movement-list` (plantilla «Lista de solo lectura con filtros»); rutas en `app.routes.ts:257-311`; modelos en `models/stock.ts`.
- Migraciones de inventory: `0001..0003`.

### Hipótesis / supuestos no confirmados
- «L-YYYYMMDD-0001 correlativo al período fiscal» se interpreta así: `YYYYMMDD` = fecha local de creación del lote; el número es correlativo por empresa y período fiscal (reinicia en 0001 al cambiar de período, no cada día). Se asume que una empresa sin período fiscal abierto para la fecha no puede crear lotes (mismo bloqueo que ventas/compras). A confirmar al revisar el PR.
- Los ajustes de existencias sobre un producto con lotes operan sobre el stock sin lote (no hay ajuste por lote en esta tarjeta).

### Módulos y dependencias relacionadas
`inventory` (dominio, aplicación, infraestructura, API, migración 0004, fachada), `accounting` (solo `services.py`, para el período), `shared/` (helper de numeración), frontend `features/inventory`, menú y i18n. Consumidores futuros del contrato: PROD-004/005/006/007/008. `costing` solo lee movimientos: no debe cambiar.

### Implementaciones similares existentes
Numeración por período (ventas/compras); `StockMovement`/`RecordMovement` (se extienden, no se duplican); `ListStock`/`StockPosition`; `movement-list` y `stock-detail` en el frontend.

### Comportamiento actual
Inventario solo conoce saldo físico por producto+almacén; cualquier salida con saldo suficiente se acepta. No hay forma de bloquear stock ni de saber de qué tanda proviene.

### Restricciones
`Decimal` para cantidades; nunca editar migraciones aplicadas (nueva `0004`); aislamiento por `company_id`; los módulos solo se hablan por `services.py`; dominio sin Django; frontend con i18n es/en/pt, sin `any`; avisar antes de instalar dependencias (ninguna prevista).

### Riesgos identificados
Cambiar las comprobaciones de saldo toca la ruta caliente de ventas/compras/ajustes (regresión); carreras en salidas concurrentes de lote y en la numeración (pruebas sobre PostgreSQL); el helper compartido toca código de ventas/compras ya en producción; dependencia de período fiscal para crear lotes.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — cambia el libro de movimientos (nueva columna y tablas), añade invariantes sobre toda salida de stock y un contrato nuevo en la fachada que usarán cinco tarjetas posteriores.

### Diseño requerido
**SI** — nueva pantalla de consulta (Lotes) y sección de lotes en el detalle de existencia.

## Diseño
Ver `docs/design/DDR-lotes-disponibilidad-inventario-pantalla-lotes.md`.

## Arquitectura
Ver `docs/adr/ADR-lotes-disponibilidad-inventario-modelo-lotes.md`.

## Plan
Ver `docs/plans/PLAN-2026-11-26-lotes-disponibilidad-inventario.md` (v1, COMPLETO, READY).

## Implementación

**Resumen.** Los lotes son una dimensión nullable del libro de movimientos (`StockMovementModel.lot`) con la entidad `StockLot`; el saldo de un lote se calcula de sus movimientos y el disponible para empaque es el físico solo si está liberado. Se **extendieron** las funciones existentes (no se creó otro registrador): `RecordMovement` acepta `lot_id`; `RecordOutputs`, `ReverseMovement` y `ReverseSourceMovements` consumen `repository.balance(..., unlotted=True)` / saldo del lote.

| Parte | Archivos principales | Cubre |
|---|---|---|
| Modelo y migración | `inventory/infrastructure/django/models.py`, `migrations/0004_stock_lots.py` | INV-07, INV-09 |
| Helper de numeración | `shared/fiscal_numbering.py`; `LotNumberingAdapter` en `inventory/infrastructure/adapters.py` | AC-03, AC-04, INV-07 |
| Dominio | `domain/lot.py`, `domain/movement.py` (`lot_id`, `production_order`), `domain/exceptions.py` | INV-04, INV-06 |
| Repositorios | `movement_repository.py` (`balance(lot_id/unlotted)`, `lot_has_movements`), `lot_repository.py` | INV-01..03 |
| Reglas de saldo | `application/movement_use_cases.py` (`check_lot_output`, `_check_lot`, reversiones) | INV-01..05, AC-07..10 |
| Casos de uso y fachada | `application/lot_use_cases.py`, `services.py` (`create_lot`, `release_lot`, `get_lot`, `list_lots_for_product`, `record_movement(lot_id=)`) | AC-01, 02, 04..06 |
| API | `api/lot_views.py`, `lot_serializers.py`, `lot_urls.py`, `config/urls.py`; `has_lots` en existencias y `lot` en movimientos | AC-11, 13 |
| Frontend | `features/inventory`: `models/lot.ts`, `services/lots-api.service.ts`, `pages/lot-list`, sección en `stock-detail`, fila en `movement-detail`, ruta `inventory/lots`, menú (`routes.json`), i18n es/en/pt | AC-14 |
| Helper en ventas/compras | `OrderNumberingAdapter` y `PurchaseNumberingAdapter` ahora llaman a `allocate_period_number` | ADR decisión 7 |

**Pruebas.** Backend: `inventory/tests/test_lots.py` (dominio, creación/idempotencia/numeración, reglas de salida con y sin lote, reversiones, API) y `test_lots_concurrency.py` (PostgreSQL con hilos: numeración y salidas simultáneas; comprobación por mutación hecha: anular el control de saldo del lote hace fallar 3 pruebas, incluida la de carrera). Frontend: `lots-api.service.spec.ts`, `lot-list.component.spec.ts`, ampliación de `stock-detail`, `stock-api`, `sidebar-menu`.

**Desviaciones respecto al plan (todas de detalle, sin cambio de Specification):**
1. La ruta de la API es `/api/stock-lots/` (consistente con `/api/stock/`, `/api/stock-movements/`), no `/api/inventory/lots/`; PLAN, ADR y `ddd.md` ya lo reflejan.
2. La lista de Lotes reutiliza la tabla responsive `inventory-table` (se apila en < 768 px, como `stock-list`/`stock-detail`) en lugar de `ngx-datatable` + tarjetas propias; los filtros son un formulario simple (4 campos) sin panel colapsable. Es coherente con el sistema de diseño y evita duplicar la variante de tarjetas.
3. `inventory → accounting` se añadió a `ALLOWED_DEPENDENCIES` de `test_boundaries.py` (el plan lo implicaba por el helper de numeración; la prueba de fronteras lo exigió explícitamente).
4. Se añadió la opción «Orden de producción» al filtro de origen de movimientos (`production_order` ya existe en el catálogo cerrado del dominio).

**Deuda técnica / notas.** (a) Los ajustes sobre un producto con lotes solo alcanzan el stock sin lote (documentado, fuera de alcance). (b) Crear lotes exige período fiscal abierto (misma decisión que ventas/compras). (c) La interpretación del código `L-YYYYMMDD-NNNN` (fecha del lote + correlativo por período fiscal) queda por confirmar en la revisión; solo afecta a `format_lot_code`. (d) Verificación visual en navegador no realizada en esta etapa.

**UI.** Pantalla de referencia: `movement-list`/`stock-list` (lista de solo lectura con filtros) y `stock-detail` (detalle con tabla embebida); componentes reutilizados: `inventory-table`, `badge-outline`, `ngb-pagination`; no se crearon componentes compartidos nuevos.

## Review
_Pendiente_

## Publicación
_Pendiente_
