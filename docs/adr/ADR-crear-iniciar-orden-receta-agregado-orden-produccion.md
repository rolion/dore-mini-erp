# ADR-crear-iniciar-orden-receta-agregado-orden-produccion: Agregado `ProductionOrder` con copia de la receta

**Estado:** Propuesto
**Task relacionado:** TASK-crear-iniciar-orden-receta
**Fecha:** 2026-11-26

## Contexto
DORE-PROD-003 pide órdenes que conserven receta, ingredientes y rendimiento aunque la receta cambie, y que elijan un almacén. El ADR de recetas ya anticipa la copia (decisión 6). Producción hoy solo depende de Catálogo (`test_boundaries.py:23`); el almacén vive en Inventario, accesible solo por `inventory/services.py`.

## Decisión
1. **Agregado `ProductionOrder`** (dominio puro, mismo módulo `production`) con líneas `ProductionOrderIngredient`. Estados `DRAFT` → `IN_PREPARATION` solo por métodos (`start(now)`, `change_plan(warehouse_id, preparations)` válido solo en borrador). Cantidad prevista y rendimiento previsto se **derivan** (`por preparación × preparaciones`), nunca se guardan multiplicados.
2. **Copia (snapshot)** al crear: id/nombre de la receta, producto resultante (id, nombre, unidad), rendimiento por preparación y, por ingrediente, producto (id, nombre), unidad (id, abreviatura) y cantidad por preparación. Las órdenes no leen la receta después; editar o desactivar la receta no las altera.
3. **Tablas** `production_order` (id UUID, company_id, number, recipe_id sin FK, snapshot de la receta, warehouse_id UUID sin FK, preparations, status, started_at, timestamps; único `(company_id, number)`; check `preparations > 0`) y `production_order_ingredient` (FK a la orden, snapshot, position). Contador `production_order_counter` (company_id único, `last_number`) bloqueado con `select_for_update` para numerar sin huecos ni duplicados.
4. **Dependencia nueva `production → inventory`** únicamente por `inventory.services` (`list_active_warehouses`, `get_warehouse_names`), mediante un puerto `WarehouseDirectory` y adaptador en `production/infrastructure/adapters.py`. Se actualiza `ALLOWED_DEPENDENCIES['production'] = {'catalog', 'inventory'}` y `MODULE_CATALOG` (`requires=('catalog', 'inventory')`).
5. **Sin efecto en existencias:** crear, editar e iniciar no llaman a movimientos de Inventario (solo lectura de almacenes). El consumo y la entrada del producto terminado son tarjetas posteriores.
6. **API aditiva** `api/production-orders/`: `GET` lista (paginada 20/100, filtro `status`), `POST` crea borrador, `GET/PUT /<id>/` (PUT solo borrador), `POST /<id>/start/`; `GET /api/production-orders/warehouses/` devuelve los almacenes activos (así el formulario no depende de la API de Inventario). `required_modules = ('production',)`.

## Alternativas consideradas
- **Referenciar la receta viva y leerla al mostrar:** viola el requisito de inmutabilidad. Descartada.
- **Guardar totales multiplicados:** duplica datos y se desincroniza al editar el borrador. Descartada.
- **No requerir `inventory` y permitir almacén opcional:** la tarjeta exige almacén. Descartada.
- **Numeración por período fiscal como Compras:** acopla Producción a Contabilidad sin necesidad. Descartada; contador simple por empresa.

## Estrategia de rollback / mitigación
Cambio aditivo (tablas y rutas nuevas, migración nueva sin tocar existentes): revertir el PR deja las tablas sin uso; una migración inversa las elimina. El cambio de `requires` solo afecta a Producción, módulo nuevo y no habilitado por defecto; si una empresa lo tuviera activo sin Inventario, el menú y la API de órdenes quedan bloqueados hasta habilitar Inventario (la validación de dependencias de Modularidad lo indica), sin pérdida de datos de recetas.

## Consecuencias
Primer acoplamiento de Producción con Inventario, acotado a lectura de almacenes. Hay que actualizar `ddd.md` (nota de Producción), `test_boundaries`, `modularity/tests/test_domain.py:31`, `test_guards.py` (`CHILD_MODELS` y padres) y el menú. Las tarjetas siguientes (completar, consumos) heredan snapshot, número y almacén.
