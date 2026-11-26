# ADR-lotes-disponibilidad-inventario-modelo-lotes: Lotes como dimensión del libro de movimientos

**Estado:** Propuesto
**Task relacionado:** TASK-lotes-disponibilidad-inventario
**Fecha:** 2026-11-26

## Contexto
Inventario calcula la existencia como suma con signo de `StockMovementModel` por producto y almacén. La tarjeta DORE-PROD-002 pide identificar por lote el granel de producción, distinguir **físico** de **disponible para empaque** (solo lotes liberados) y bloquear el consumo del granel en refrigeración. Las tarjetas siguientes (PROD-004/005/007/008) crearán, liberarán y consumirán lotes; esta solo entrega la capacidad en Inventario y su consulta.

## Decisión
1. **Entidad `StockLot` propia de Inventario** (`inventory_stock_lot`): `id`, `company_id`, `product_id` (UUID, sin FK a catálogo), `warehouse` (FK al almacén), `code`, `fiscal_period_id`/`fiscal_period_name`/`number`, `lot_date`, `status` (`refrigerating` | `released`), `released_at`, `released_by_id`/`released_by_name`, `created_at`. Un lote pertenece a **un producto y un almacén**. Únicos: `(company_id, code)` y `(company_id, fiscal_period_id, number)`. El estado «en refrigeración → liberado» es un método del agregado (`lot.release(...)`), idempotente.
2. **El lote es una dimensión del libro, no un segundo libro:** `StockMovementModel.lot` (FK nullable al lote, `PROTECT`). Físico del lote = suma con signo de sus movimientos; **disponible = físico si está liberado, 0 si está en refrigeración**. Sin tabla de saldos: se calcula, como hoy.
3. **Reglas (invariantes, todas bajo el bloqueo del almacén que ya serializa los movimientos):**
   - INV-L1: el saldo de un lote nunca es negativo (tampoco con la política de stock negativo).
   - INV-L2: una salida **con** lote solo se acepta si el lote está liberado y alcanza su saldo; es lo que usará el empaque.
   - INV-L3: una salida **sin** lote solo puede consumir el **stock sin lote** (físico − suma de saldos de lotes). Con la política de stock negativo activa, este remanente puede quedar negativo como hoy; los lotes nunca se tocan.
   - INV-L4: la entrada a un lote solo se crea junto con el lote (`create_lot`); no se agrega stock a un lote existente.
   - INV-L5: un contramovimiento (reversión) hereda el lote del original, no exige estado liberado pero sí saldo del lote ≥ cantidad (INV-L1).
   - INV-L6: un producto sin lotes se comporta exactamente como hoy (físico = disponible; sin cambios de reglas).
4. **No se duplican funciones:** se **extienden** las existentes. `RecordMovement` recibe `lot_id` opcional y sus tres controles de saldo (`_check_balance`, `RecordOutputs._check_balances`, y los de las reversiones) pasan a pedir al repositorio el **saldo consumible** (`consumable_balance(product, warehouse, lot_id)`), único punto que conoce la regla del lote; `ListStock`/`GetStockPosition` reutilizan `list_balances`. Nuevo solo lo que no existe: `StockLot`, `CreateLot`, `ReleaseLot`, `ListLots`, repositorio de lotes, helper de numeración.
5. **Fachada** (`inventory/services.py`, con `company_id` primero): `create_lot(...)` crea el lote **en refrigeración** y su entrada en una sola transacción, idempotente por el origen del movimiento (`source_type`/`source_id`, p. ej. `production_order`); `release_lot(...)` idempotente; `record_movement(..., lot_id=...)` para salidas con lote; `get_lot(s)` y `get_lot_balances(...)` (físico y disponible) para Producción. Se añade `production_order` a `SOURCE_TYPES`. La regla de «mínimo de horas antes de liberar» **no** vive aquí (PROD-005); Inventario solo cambia el estado.
6. **Código `L-YYYYMMDD-0001`:** `YYYYMMDD` = fecha local del lote; número correlativo por empresa y período fiscal (reinicia al cambiar de período), con ancho mínimo 4 y creciendo si se supera. Se asigna dentro de la transacción de `create_lot`, tras validar, para no gastar números. Sin período abierto para la fecha: se rechaza con `fiscal_period_missing` / `fiscal_period_closed` (409), como ventas y compras.
7. **Tercer consumidor de numeración → helper compartido.** El ADR de compras (decisión 8) difirió la extracción hasta un tercer consumidor. Se crea `shared/fiscal_numbering.py::allocate_period_number(company_id, on_date, counter_model)` (bloquea el período abierto con `accounting.services.lock_open_period`, incrementa el contador con `select_for_update` y devuelve `(PeriodRef, número)`; deja pasar las excepciones de contabilidad para que cada módulo las traduzca a su excepción de dominio). Inventario lo usa desde el primer día (nueva dependencia permitida `inventory → accounting`, solo por `services` y desde su adaptador; se añade al mapa de `test_boundaries.py`); los adaptadores de ventas y compras se migran a él en un **paso final aislado** (sin cambio de esquema ni de datos; mismas tablas de contador), cubierto por sus pruebas de carrera existentes. Si ese paso revela riesgo, se difiere sin afectar el resto.
8. **Consulta:** `GET /api/stock-lots/` (paginado, como el resto de recursos de Inventario; filtros `search` por código, `product_id`, `warehouse_id`, `status`, `with_stock`) y `GET /api/stock-lots/<id>/`; cada lote devuelve producto, almacén, código, estado, `physical_quantity`, `available_quantity`, fechas y liberación. Las existencias por producto/almacén **no cambian de significado**: se añade solo `has_lots` (aditivo) y el movimiento expone `lot_id`/`lot_code`. Sin endpoints de alta/liberación (decisión del usuario); solo lectura bajo `required_modules=('inventory',)`.
9. **Producción deshabilitada o inexistente:** no hay lotes y las reglas no intervienen. Las reglas dependen de los **datos** (lotes existentes), no del interruptor del módulo: si Producción se deshabilita después, los lotes y su bloqueo se conservan.

## Alternativas consideradas
- **Tabla de saldos por lote materializada:** más rápida de leer pero duplica la verdad del libro y exige mantenerla en cada reversión; descartada (el volumen no lo justifica y rompe «el saldo se calcula»).
- **Un producto distinto por estado** («cuñapé en refrigeración» / «cuñapé liberado») con transferencias: no identifica el lote, rompe costos y recetas; descartada.
- **Almacén «Refrigeración» como bloqueo:** confunde ubicación con disponibilidad y duplicaría saldos al liberar; descartada.
- **Salida sin lote que consume lotes liberados (FIFO):** el sistema decidiría de qué lote sale; descartada por el usuario.
- **Numeración local sin helper** (copiar el adaptador por tercera vez): descartada por el pedido de no duplicar y por el compromiso del ADR de compras.

## Estrategia de rollback / mitigación
- Migración `inventory/0004` **aditiva** (tablas nuevas y columna `lot` nula en movimientos); no migra datos. Revertir el código deja columna y tablas sin uso sin pérdida; sin lotes, el comportamiento es idéntico al actual (INV-L6).
- El despliegue ya hace backup antes de `migrate`; se recomienda probar la migración contra una copia con movimientos existentes.
- Las reglas nuevas solo aplican a productos con lotes; ningún dato existente tiene lote, así que el riesgo de regresión se concentra en la refactorización de los controles de saldo, cubierta por las pruebas existentes de movimientos, salidas, reversiones, política negativa y ajustes más las nuevas.
- El paso del helper en ventas/compras es independiente: se puede revertir en su propio commit.

## Consecuencias
- Crear un lote exige período fiscal abierto para la fecha (misma decisión que ventas/compras).
- Los ajustes de existencias sobre un producto con lotes solo alcanzan el stock sin lote; ajustar un lote queda para una tarea futura.
- Quedan fijados el contrato `create_lot`/`release_lot`/`record_movement(lot_id)` y las consultas de saldo por lote que usarán PROD-004..008.
- `SOURCE_TYPES` crece con `production_order`; PROD-004 decide qué reversiones desde Inventario se bloquean para ese origen.
