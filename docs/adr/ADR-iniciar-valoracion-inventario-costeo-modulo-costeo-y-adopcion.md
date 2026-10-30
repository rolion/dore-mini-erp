# ADR-iniciar-valoracion-inventario-costeo-modulo-costeo-y-adopcion: Módulo `costing` y adopción de valoración como corte inmutable

**Estado:** Propuesto
**Task relacionado:** TASK-iniciar-valoracion-inventario-costeo
**Fecha:** 2026-10-30

## Contexto
No existe ningún concepto de costo. Hay que registrar una base monetaria inicial sobre las existencias sin tocar el libro de cantidades (`StockMovementModel`), detrás de una capacidad opcional «Costeo», con dinero en `Decimal` y aislamiento por `company_id`.

## Decisión
1. **Módulo nuevo `costing`** (`backend/modules/costing/` con `domain/ application/ infrastructure/ api/`). Se agrega a `MODULE_CATALOG` como `ModuleDefinition('costing', 'Costeo', 'Valoración y costo de las existencias.', requires=('inventory',))`, fuera de `DEFAULT_ENABLED_KEYS`. La API (`/api/valuation/`) usa el permiso por módulo existente con la clave `costing`.
2. **Agregado `ValuationAdoption`** (dominio puro): una por empresa, inmutable. Contiene `cutoff_at`, usuario, método fijo `weighted_moving_average` y líneas `ValuationLine` (producto, `reconciled_quantity`, `total_value`, `unit_cost`, `declared_zero`, `source`). Solo se crea con `ValuationAdoption.adopt(...)`; no hay métodos de edición ni borrado.
3. **Dinero y redondeo:** `total_value` Decimal(16,2) en BOB (≥ 0, 2 decimales máx.); `unit_cost = total_value / reconciled_quantity` con `ROUND_HALF_UP` a **6 decimales** (Decimal(18,6)), regla explícita y única en el dominio. El valor total es la fuente de verdad; el costo unitario es derivado y se muestra a 6 decimales (2 en listados resumidos). Nunca `float`.
4. **Costo ausente vs cero:** el valor de una línea es obligatorio; `total_value = 0` solo es válido con `declared_zero = true`; `declared_zero` con valor > 0 es inválido. Una línea sin valor es «Pendiente» y bloquea la adopción (400 con errores por línea).
5. **Conciliación bajo bloqueo:** el cliente envía `adoption_id` (UUID, idempotencia) y por cada producto su `reconciled_quantity`. `AdoptValuation` toma el bloqueo de todos los almacenes de la empresa mediante una función nueva de la fachada `inventory.services.lock_company_stock(company_id)` (orden por id para evitar interbloqueos), lee `inventory.services.get_company_balances(company_id)` (saldo total por producto, suma de almacenes, solo productos que controlan stock con saldo ≠ 0) y: (a) si algún saldo es negativo → 409 `negative_stock` con las líneas; (b) si el conjunto de productos o alguna cantidad difiere de lo enviado → 409 `stock_changed` con esperado/actual; (c) si ya existe adopción: mismo `adoption_id` y mismo contenido → réplica 200, otro → 409 `valuation_already_adopted`. Todo o nada.
6. **No toca el libro:** no se crean movimientos ni aperturas; el corte solo copia cantidades a la tabla de Costeo. El historial son las filas inmutables (`CHECK`/sin endpoints de edición); un cambio futuro de valores será un hecho nuevo, nunca un recálculo del pasado.
7. **Tablas** (migración `costing/0001`): `costing_valuation_adoption` (`id` = adoption_id, `company_id` único, `cutoff_at`, `method`, `user_id`, `user_name`, `created_at`) y `costing_valuation_line` (`adoption` FK, `company_id`, `product_id` sin FK, `reconciled_quantity` Decimal(16,4), `total_value`, `unit_cost`, `declared_zero`, `source`; único `(adoption, product_id)`; `CHECK total_value >= 0`, `CHECK reconciled_quantity > 0`).
8. **Lecturas:** `GET /api/valuation/` (estado + adopción con líneas y nombres/unidad vía `ProductDirectory`), `GET /api/valuation/proposal/` (propuesta de conciliación: líneas con desglose por almacén y bloqueos), `POST /api/valuation/adopt/`. Estado «adoptada» se deriva de la existencia de la adopción; es la señal para que el futuro costeo la exija.
9. **Dependencias:** `costing → inventory` (solo `inventory.services`) y `costing → catalog` solo a través de la fachada de inventario (nombres/unidad); `modularity` no importa `costing`.

## Alternativas consideradas
- **Guardar el costo en `StockMovementModel`** (columna `unit_cost`): altera un libro inmutable de otro task y mezcla cantidades con dinero; descartada.
- **Estado dentro de Inventario sin módulo nuevo:** descartada por el usuario (módulo «Costeo» explícito).
- **Corte retroactivo con fecha elegida:** exigiría reconstruir saldos a una fecha y conciliar movimientos posteriores; fuera de alcance (corte = confirmación).
- **Costo por almacén:** la tarjeta fija un costo por producto y empresa; las cantidades siguen separadas en el libro.

## Estrategia de rollback / mitigación
La migración solo crea tablas nuevas (reversible con `migrate costing zero`); ningún dato existente cambia. Deshabilitar el módulo `costing` bloquea la API con 403 sin perder datos. Una adopción errónea no se edita: se corrige con una task futura de revaluación; mientras tanto la bloquea la confirmación en dos pasos (resumen).

## Consecuencias
- Nace la noción de «valoración adoptada» sin afectar ventas, compras ni reportes.
- `MODULE_CATALOG` crece (tests de modularity y pantalla de módulos se actualizan).
- La corrección de valores adoptados y el costeo de consumos posteriores quedan para tareas siguientes.
