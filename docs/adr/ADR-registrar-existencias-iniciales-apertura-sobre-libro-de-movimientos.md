# ADR-registrar-existencias-iniciales-apertura-sobre-libro-de-movimientos: La apertura se registra en el libro de movimientos de PB-INV-004

**Estado:** Propuesto
**Task relacionado:** TASK-registrar-existencias-iniciales
**Fecha:** 2026-10-28
**Reemplaza a:** `ADR-registrar-existencias-iniciales-movimientos-saldos-idempotencia` (marcado «Reemplazado por» este documento)

## Contexto
La primera versión de este task (ADR anterior) creaba sus propias tablas `StockMovement` y `StockBalance` y la migración `inventory/0002`. Mientras tanto se integró en `main` el PR #21 (PB-INV-004, `ADR-inventario-movimientos-trazables-registro-idempotente-y-saldo`), que define el libro de movimientos de Inventario: `StockMovementModel` inmutable (`kind` `in`/`out`, `quantity` > 0 con 4 decimales, origen `source_type/source_id/source_line`, reversión por contramovimiento), idempotencia por operación de origen, **saldo calculado** del libro (sin tabla de saldos), la fachada `inventory.services`, el proveedor de `shared.stock_history` y la actividad real de almacén. Ambos tasks creaban `inventory_stock_movement` e `inventory/0002`: conflicto de migraciones y de modelo (el usuario decidió integrar #21 primero y rebasar este task sobre él).

## Decisión
1. **Sin tablas ni migraciones nuevas.** La apertura crea **una entrada (`in`) por línea** con la función de registro de #21 (`RecordMovement`): `reference` = referencia de apertura, `reason` = «Apertura de existencias», `occurred_at` = la fecha de la apertura (ahora, si es hoy; si no, mediodía local de ese día) y origen `(inventory_opening, <opening_id>, '')`. Se agrega `inventory_opening` («Apertura de existencias», módulo `inventory`) al catálogo cerrado `SOURCE_TYPES`. El saldo es el del libro (`get_balance`); no existe `StockBalance`.
2. **Agregado `StockOpening`** (dominio, ya existente en este task): valida ≥ 1 línea, sin productos repetidos, cantidad ≥ 0 con ≤ 3 decimales (`^\d+(\.\d+)?$`), referencia obligatoria (≤ 100), fecha no futura. `RegisterOpening` (aplicación) lo compone con `RecordMovement` de #21 y con un puerto de lectura nuevo sobre el libro.
3. **Todo o nada e idempotente:** `RegisterOpening` abre `repository.locked(almacén)` (la transacción y el bloqueo de #21, reentrante) y dentro: (a) si ya hay movimientos con el origen `(inventory_opening, opening_id)`, compara contenido (almacén, referencia, fecha y líneas con cantidad > 0): igual → réplica (200), distinto → 409 `opening_id_reused`; (b) valida almacén activo, productos (existen, controlan stock, fracciones, vía `ProductDirectory` de #21) y que ningún par producto+almacén tenga movimientos previos → si no, 409 `stock_history_exists` con las líneas afectadas; (c) registra las entradas. Cualquier excepción deshace todas.
4. **Cantidad 0.** El libro exige cantidad > 0 (INV de #21, `CHECK`), por lo que una línea con cantidad 0 **no genera movimiento**: se acepta como entrada de la apertura, pero el producto queda sin historial (saldo 0) y podrá abrirse más adelante. Sustituye al comportamiento anterior (movimiento con cantidad 0 que consumía la apertura). Una apertura con todas las líneas en 0 es válida y no registra nada.
5. **Lecturas:** `GET /api/stock/` (existencias por producto/almacén: suma con signo del libro, agrupada; nombre y unidad vía `ProductDirectory`), `GET /api/stock/opening-check/` (pares con movimientos). Los movimientos de un producto se leen con `GET /api/stock-movements/?product_id&warehouse_id` y la pantalla de movimientos de #21; este task no define endpoint ni pantalla de movimientos propios.
6. **Dependencias:** `inventory → catalog` ya declarada por #21; el adaptador `CatalogProductDirectory` de #21 sustituye al adaptador de este task. Los métodos nuevos del repositorio del libro (`products_with_history`, `find_by_source_id`, `list_balances`) viven en `DjangoStockMovementRepository`.

## Alternativas consideradas
- **Mantener el modelo propio y reconciliar migraciones:** dos tablas de movimientos o una migración que reescriba la de #21; dos fuentes de verdad del saldo. Descartada (decisión del usuario).
- **Permitir cantidad 0 en el libro (cambiar el `CHECK` de #21):** altera un invariante mergeado y de otro task; descartada.
- **Idempotencia solo por la restricción única de #21 (`source_id=opening_id`, por producto):** no detecta una apertura reenviada con otro almacén u otras líneas; por eso se compara el contenido completo.
- **Endpoint de movimientos propio:** duplica `/api/stock-movements/`; descartado.

## Estrategia de rollback / mitigación
No hay migración: revertir es quitar las rutas `/api/stock/` y el tipo de origen `inventory_opening` (los movimientos ya registrados con ese origen seguirían en el libro, legibles; su etiqueta se mostraría como clave). Desactivar el módulo `inventory` bloquea la API con 403 sin perder datos. Las aperturas erróneas se corrigen revirtiendo cada movimiento con `reverse_movement` (contramovimiento) mientras no exista la pantalla de ajustes.

## Consecuencias
- El saldo y el historial son los de #21; una apertura posterior a cualquier movimiento (venta, compra) se rechaza porque ya hay historial del par.
- Registrar una apertura bloquea, vía el proveedor de `stock_history` de #21, cambiar la unidad base o el control de stock del producto (PB-INV-001).
- Cambios menores de comportamiento respecto al plan v1: cantidad 0 sin movimiento; el listado de Existencias se ordena por almacén y producto no por nombre; «Movimientos» usa la pantalla de #21.
