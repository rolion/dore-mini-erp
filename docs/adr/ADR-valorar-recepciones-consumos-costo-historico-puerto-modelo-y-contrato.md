# ADR-valorar-recepciones-consumos-costo-historico-puerto-modelo-y-contrato: Valoración de movimientos por un puerto neutro, promedio móvil y snapshot inmutable

**Estado:** Propuesto
**Task relacionado:** TASK-valorar-recepciones-consumos-costo-historico
**Fecha:** 2026-10-30

## Contexto
Tras la adopción (PB-VAL-001) hay una base monetaria por producto, pero ningún movimiento tiene costo. Hay que valorar entradas (recepciones, ajustes positivos) y salidas (entregas, ajustes negativos) con promedio ponderado móvil, conservando un snapshot por movimiento, sin tocar el libro de cantidades, sin que Inventario importe Costeo y sin que ningún camino que inserte movimientos escape de la valoración.

## Decisión
1. **Puerto neutro `shared/stock_valuation.py`** (patrón de `shared/stock_history.py`): Costeo registra un proveedor al arrancar (`CostingConfig.ready`). Inventario lo invoca **dentro de la sección crítica** de `RecordMovement`, `RecordOutputs` y `ReverseMovement`, justo antes de `insert`. Contrato: `is_valued(company_id) -> bool` (existe adopción) y `value_movement(company_id, request) -> None` que registra la valoración o lanza `ValuationRejected(code, message)`. Sin proveedor o sin adopción es no-op (empresas sin Costeo, sin cambios de comportamiento).
2. **Estado «valorado» = existe adopción**, no el interruptor del módulo (decisión del usuario): la valoración sigue aplicándose con Costeo deshabilitado. El módulo `costing` solo gobierna la API de consulta (`/api/valuation/…`) y las pantallas.
3. **Modelo (migración `costing/0002`, solo tablas nuevas):**
   - `costing_product_cost` — estado corriente: `company_id`, `product_id` (único por empresa), `quantity` Decimal(16,4), `total_value` Decimal(16,2). Se inicializa de las líneas de la adopción (en la propia adopción para productos con saldo; creación perezosa en cero para los demás).
   - `costing_movement_valuation` — snapshot **solo inserción**: `movement_id` (único, sin FK), `company_id`, `product_id`, `kind` (in/out), `quantity`, `unit_cost` Decimal(18,6), `value` Decimal(16,2), `average_before`/`average_after` Decimal(18,6), `quantity_after`, `total_value_after`, `cost_origin` (`purchase_price` | `manual_adjustment` | `average_at_exit` | `reversal_snapshot`), `source_type`, `source_id`, `occurred_at`, `reverses_movement_id`. Sin endpoints ni casos de uso de edición o borrado.
   - Cambio en el esquema de adopción: la adopción también escribe `costing_product_cost` (misma transacción) — implica tocar `AdoptValuation`, no sus tablas.
4. **Reglas de cálculo (dominio puro `costing/domain/costing.py`):** promedio = `total_value / quantity` (6 decimales, `ROUND_HALF_UP`, reutiliza `compute_unit_cost`). *Entrada:* `value = (cantidad × costo_unitario).quantize(0.01, ROUND_HALF_UP)` con `costo_unitario` = precio de compra (recepción) o `total_value/cantidad` (ajuste positivo, valor total explícito); estado `quantity += q`, `total += value`. *Salida:* `unit_cost = average vigente`; `value = (q × average).quantize(0.01)`; si `q == quantity` del estado, `value = total_value` completo (sin residuo); estado `quantity -= q`, `total -= value`. *Reversión:* de una entrada, solo si ningún movimiento valorado posterior del producto existe (si no → `valuation_blocked`); sale al costo del snapshot original. De una salida: entra al `unit_cost` del snapshot original (`reversal_snapshot`), sin revalorar nada anterior.
5. **Restricciones en inventario valorado** (todas bajo bloqueo): (a) sin saldos negativos — `ModularityInventoryPolicy.allow_negative_stock()` devuelve `False` si `stock_valuation.is_valued(company)` aunque la política de la empresa lo permita; (b) sin retroactividad — un movimiento valorado con `occurred_at` anterior al último valorado del producto o al corte → `valuation_blocked`; (c) entrada sin valor → `valuation_required` (400, error de campo).
6. **Cómo llega el valor a la entrada:** `inventory.services.record_movement`/`record_outputs` aceptan `valuation: MovementValuation | None` (DTO inmutable: `unit_cost` o `total_value`, `declared_zero`, `cost_origin`). Compras pasa el `unit_price` de la línea de la compra (`purchase_price`); el ajuste positivo recibe `total_value` + `declared_zero` del cliente (`manual_adjustment`); las salidas no llevan valor (lo fija el promedio).
7. **Bloqueo y orden:** además del bloqueo del almacén, el proveedor toma `SELECT … FOR UPDATE` de la fila `costing_product_cost` del producto; en `RecordOutputs` los productos se procesan **ordenados por `product_id`**. Todo en la transacción del movimiento: si algo falla no queda valoración ni movimiento.
8. **Contrato API (lectura, módulo `costing`):** `GET /api/valuation/movements/` (filtros `product_id`, `source_type`, `source_id`, `movement_id`, `date_from`, `date_to`, `page`) y `GET /api/valuation/costs/` (costo corriente por producto). Montos y cantidades como cadenas decimales. **Compatibilidad:** `POST` de ajuste (`/api/stock-adjustments/`) admite `total_value`/`declared_zero` opcionales (obligatorios solo con inventario valorado y diferencia positiva); respuestas existentes no cambian. Errores: 400 `valuation_required`/`valuation_invalid`, 409 `valuation_blocked` (retroactividad, reversión) con mensaje accionable.
9. **Dependencias:** `inventory → shared.stock_valuation ← costing`; `costing → inventory.services` (ya existente); `purchases → inventory.services` (ya existente); ningún módulo importa a `costing`.
10. **Extensión PB-CST-002:** las entradas de producción usarán `cost_origin='production_cost'` mediante el mismo DTO; no se implementa aquí.

## Alternativas consideradas
- **Columna de costo en `StockMovementModel`:** altera el libro inmutable y mezcla dinero con cantidades (ya descartada en PB-VAL-001).
- **Cada módulo llama a Costeo tras registrar el movimiento:** deja huecos (cualquier camino nuevo o la reversión escapa); no garantiza atomicidad con la política de saldo.
- **Eventos asíncronos:** la salida debe fijar el costo vigente al confirmarse; un evento diferido rompería el snapshot y la restricción de confirmar sin valoración.
- **Recalcular el promedio desde el historial en cada consulta:** costoso y reabre el pasado; se guarda estado corriente más snapshot.
- **Valorar solo con el módulo habilitado:** abre huecos de costo (descartada por el usuario).

## Estrategia de rollback / mitigación
La migración solo crea tablas nuevas (`migrate costing 0001` las elimina). Sin adopción, el puerto es no-op: el comportamiento para empresas sin Costeo es idéntico al actual (verificado por la suite existente de Inventario, Compras y Ventas). Si hay un defecto tras desplegar, el puerto se desregistra (proveedor `None`) sin migrar datos: los movimientos nuevos quedarían sin snapshot y una nueva task de conciliación los valoraría; por eso el snapshot es la fuente y no se recalcula el pasado. Una valoración errónea no se edita: la corrección es una task futura con validación de impacto.

## Consecuencias
- Cada movimiento de una empresa valorada tiene snapshot; consultar costo es una lectura simple.
- Aparece acoplamiento runtime vía puerto (aceptado, mismo patrón que `stock_history`).
- Ajustes positivos y la apertura de existencias dejan de funcionar sin valor en empresas valoradas (la apertura solo existe sin historial).
- Las correcciones y revaluaciones, la producción y el costeo en reportes quedan para tareas siguientes.
