# ADR-liberar-lote-despues-refrigeracion-minimo-y-liberacion: Mínimo de refrigeración y liberación del lote

**Estado:** Propuesto
**Task relacionado:** TASK-liberar-lote-despues-refrigeracion
**Fecha:** 2026-11-27

## Contexto
PROD-005 pide impedir la liberación antes de un mínimo de horas configurable y, al liberar, pasar la orden a «Listo para empacar» y el lote a disponible. Inventario ya libera lotes (`release_lot`, idempotente, sin movimientos) y deja la regla del mínimo a Producción. Los ajustes por empresa viven en Modularidad y hoy solo admiten `choice`/`percent`/`boolean`.

## Decisión
1. **Regla en el dominio de Producción:** `ProductionOrder.releasable_from(min_hours) = entered_at + min_hours` y `ProductionOrder.release(now, min_hours, actor)`: solo desde `refrigerating`; rechaza si `now < releasable_from` (`ReleaseTooEarly`, con la hora habilitada); pasa a `ready_to_pack` y guarda `released_at`, `released_by_id`, `released_by_name`. `now` es siempre el reloj del servidor.
2. **Caso de uso `ProductionOrders.release`** bajo `select_for_update` de la orden: si ya está `ready_to_pack`, devuelve la orden sin tocar nada (idempotente); si no, valida el mínimo, llama a Inventario por un puerto (`StockGateway.release_lot`, adaptador sobre `inventory.services.release_lot`) y guarda la orden, todo en la misma transacción. Liberar no crea movimientos: el físico (118) no cambia y el disponible pasa a 118.
3. **Mínimo como ajuste por empresa** `production.min_refrigeration_hours` (módulo `production`), tipo nuevo **`integer`** (0–720, valor inicial 12; 0 = sin espera). Se agrega el tipo al catálogo, a su validación/`display` y a la pantalla de Ajustes (aditivo; los otros tipos no cambian). Producción lo lee con un puerto `ReleasePolicy` y adaptador sobre una nueva fachada `modularity.services.get_production_settings(company_id)`.
4. **Frontera:** `production → modularity` (solo fachada de lectura, como Inventario) se agrega a `test_boundaries` y a `docs/architecture/ddd.md`.
5. **API:** `POST api/production-orders/<id>/release/` (módulo `production`); el detalle de la orden suma `release`: `{min_hours, releasable_from, can_release}` y `released_at`/`released_by`. Error 409 `release_too_early` con `releasable_from` y `min_hours`; 409 de estado si la orden no está en refrigeración.
6. **Migración aditiva** `production/0004`: `released_at`, `released_by_id`, `released_by_name` en la orden (nulos/vacíos) y el estado `ready_to_pack` en las opciones.

## Alternativas consideradas
- **Regla en Inventario:** contradice el ADR de lotes (Inventario solo cambia estado) y mezcla una política de producción con el libro.
- **Constante o variable de entorno para las horas:** no es configurable por la operación; descartada.
- **Congelar el mínimo vigente al ingresar el lote:** más complejo; hoy basta evaluar con el valor vigente al liberar (S2).
- **Guardar `releasable_from` en la orden:** duplica un dato derivable y queda obsoleto si cambia el ajuste.

## Estrategia de rollback / mitigación
Migración aditiva y reversible (columnas nulas). Revertir el despliegue deja las órdenes `ready_to_pack` con lote ya liberado en Inventario, que sigue siendo coherente; las órdenes en refrigeración simplemente no podrían liberarse hasta restaurar. El tipo nuevo de ajuste es aditivo: sin valor guardado rige el 12 inicial.

## Consecuencias
Producción depende ahora de Modularidad por su fachada. La liberación no es deshacible (fuera de alcance). PROD-007 (empaque) parte de órdenes `ready_to_pack` y lotes liberados. Si el mínimo se baja o sube, afecta a los lotes aún no liberados.
