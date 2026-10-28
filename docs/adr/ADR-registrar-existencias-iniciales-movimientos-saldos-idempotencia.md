# ADR-registrar-existencias-iniciales-movimientos-saldos-idempotencia: Movimientos, saldos y apertura idempotente

**Estado:** Propuesto
**Task relacionado:** TASK-registrar-existencias-iniciales
**Fecha:** 2026-10-27

## Contexto
La apertura es la primera escritura de existencias. Crea el modelo que reutilizarán ajustes, compras y ventas, y debe cumplir: un movimiento de apertura y su saldo por producto+almacén, sin duplicados ante doble clic o reintento, y solo si no hay movimientos previos de ese par. Además hay dos puertos «listos» de PB-INV-001/002 que hoy no tienen datos (`shared.stock_history`, `WarehouseActivity`). `inventory` necesita datos del producto (controla stock, unidad base, si admite fracciones), que pertenecen a `catalog`.

## Decisión
1. **Modelo en `inventory`.** `StockMovement` (inmutable, append-only: `id`, `company_id`, `warehouse` FK interna, `product_id` UUID sin FK, `movement_type` = `opening`, `quantity` Decimal(14,3) con signo, `movement_date`, `reference`, `opening_id`, `created_by_id`, `created_at`) y `StockBalance` (`company_id`, `warehouse`, `product_id`, `quantity`, `updated_at`; único por empresa+almacén+producto). El saldo se actualiza en la misma transacción que el movimiento; no hay recálculo asíncrono. Un movimiento nunca se edita ni se borra.
2. **Agregado `StockOpening`** (dominio, sin Django): almacén, fecha, referencia, `opening_id` y líneas (producto, cantidad). Valida forma y reglas puras: ≥ 1 línea, sin productos repetidos, cantidad ≥ 0 con ≤ 3 decimales, fecha no futura, referencia obligatoria. Las reglas que dependen de otros datos las comprueba el caso de uso `RegisterOpening`: almacén de la empresa y activo, cada producto controla stock (vía puerto), cantidad entera si la unidad no admite fracciones, y que el par producto+almacén no tenga movimientos.
3. **Puerto `StockProductCatalog` (inventory/application/ports.py)** implementado por un adaptador que usa solo `modules.catalog.services`, que gana `get_stock_products(company_id, product_ids) -> dict[UUID, StockProduct]` con DTO inmutable (`id`, `name`, `active`, `tracks_stock`, `base_unit_id/name/abbreviation/allows_fractions`). `ALLOWED_DEPENDENCIES['inventory'] = {'catalog'}`. Catalog no importa inventory.
4. **Idempotencia por clave del cliente.** El formulario genera un `opening_id` (UUID) al abrirse y lo reenvía en cada intento. `RegisterOpening` toma un bloqueo de fila sobre el almacén (`select_for_update`), con lo que serializa aperturas concurrentes del mismo almacén y evita la carrera entre claves distintas; si ya existen movimientos con ese `opening_id` y el contenido (almacén, fecha, referencia, líneas) es el mismo, **devuelve el resultado original** (HTTP 200 en vez de 201, sin crear nada); si el contenido difiere, 409 `opening_id_reused`. Restricciones de base como defensa final: único `(company_id, opening_id, product_id)` y único parcial `(company_id, warehouse_id, product_id)` donde `movement_type='opening'`; un `IntegrityError` se resuelve releyendo (réplica) o devolviendo 409 `stock_history_exists`.
5. **Todo o nada.** La apertura es una sola transacción: si una línea es inválida o ya tiene movimientos, no se crea ninguna. Errores de forma/regla por línea: 400 con `lines[i].<campo>`; líneas con movimientos previos: 409 `stock_history_exists` con `lines: [{index, product_id}]` para que la UI las señale.
6. **Conectar los puertos.** `InventoryConfig.ready()` registra en `shared.stock_history` un proveedor que consulta `StockMovement` (empresa+producto). `DeactivateWarehouse` pasa a usar un adaptador real (`has_nonzero_balance` consulta `StockBalance ≠ 0`; `has_pending_receipts` sigue en «no» hasta la historia de recepciones). Con esto Catálogo bloquea cambiar unidad/control de stock tras la apertura, como ya especificó PB-INV-001.
7. **Lectura mínima** en `inventory/api`: saldos por almacén (enriquecidos con nombre y unidad vía puerto), movimientos de un par producto+almacén, y verificación de historial para marcar líneas en el formulario. Solo lecturas; sin ajustes ni transferencias.
8. **Catálogo, cambios aditivos:** filtro `tracks_stock` en `GET /api/products/` y `allows_fractions` en `base_unit`.

## Alternativas consideradas
- **Solo movimientos, saldo calculado con `SUM`:** más simple, pero cada consulta de existencias recorre el historial y el criterio pide «movimiento y saldo correspondiente». Descartada.
- **Idempotencia solo por la restricción natural (producto+almacén):** impide duplicar, pero el reintento recibiría un error en vez del resultado original, y el usuario vería «ya tiene movimientos» tras un envío que sí tuvo éxito. Se mantiene como defensa final, no como único mecanismo.
- **Tabla de documentos `StockOpening` persistida:** añade una tabla que no aporta información que no tengan los movimientos (referencia y `opening_id` viajan en ellos). Descartada; el agregado existe solo en dominio/aplicación.
- **Eventos de dominio para actualizar saldos:** infraestructura nueva fuera del MVP (`CLAUDE.md`). Descartada.
- **Clave de idempotencia por cabecera HTTP:** equivalente, pero el campo en el cuerpo es más simple de validar y probar con el serializer actual.

## Estrategia de rollback / mitigación
- Migración `inventory/0002` solo aditiva (dos tablas nuevas). Rollback: `migrate inventory 0001` elimina únicamente tablas nuevas; ningún dato previo cambia.
- Datos ya cargados no se corrigen editando: se corrigen con ajustes (historia posterior) — si hubiese una apertura errónea antes de que existan ajustes, se resuelve con intervención técnica, no con la API; se anota como limitación conocida.
- Desactivar el módulo `inventory` bloquea la API de existencias con 403 sin perder datos.
- Registro de puertos solo en `ready()`: si se quita, vuelve el comportamiento previo («sin historial»).

## Consecuencias
- Ajustes, compras y ventas futuras reutilizan `StockMovement`/`StockBalance` y añaden tipos de movimiento; ya existe la restricción parcial por tipo `opening` y un `CheckConstraint` que exige cantidad ≥ 0 en aperturas.
- Una apertura con cantidad 0 también «consume» la única apertura posible del par.
- Se paga una consulta extra al catálogo por apertura/listado (lote por IDs, no N+1).
- Hay que actualizar `docs/architecture/ddd.md` (modelo de inventario, dependencia `inventory → catalog`, estado de los puertos).
