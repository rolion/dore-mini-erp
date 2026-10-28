# ADR-inventario-movimientos-trazables-registro-idempotente-y-saldo: Libro de movimientos, idempotencia por operación de origen y saldo

**Estado:** Propuesto
**Task relacionado:** TASK-inventario-movimientos-trazables
**Fecha:** 2026-10-28

## Contexto
Inventario necesita un registro inmutable de entradas y salidas del que se derive el saldo, que no duplique movimientos ante reintentos y que sea consultable (lista/detalle). Hoy los puertos `shared/stock_history` y `WarehouseActivity` responden «no» a la espera de esta historia (ADR de PB-INV-001/002). Ventas, Compras y Ajustes aún no existen como productores; deben poder llamar a Inventario sin acoplarse a su infraestructura.

## Decisión
1. **Agregado `StockMovement` en `inventory`**, append-only: `id`, `company_id`, `product_id`, `warehouse_id`, `kind` (`in`/`out`), `quantity` (`Decimal` > 0, 4 decimales), `occurred_at`, `user_id` y `user_name` (snapshot), `reference`, `reason`, origen (`source_type`, `source_id`, `source_line`), `status` (`confirmed`/`reversed`), `reverses_id`. No hay métodos de edición ni borrado; el único cambio permitido tras crear es `confirmed → reversed`, hecho por `reverse()` en el repositorio dentro de la misma transacción que crea el contramovimiento.
2. **Catálogo cerrado de clases de origen** en el dominio (`SourceType`: `sales_order` → módulo `sales`, `purchase_receipt` → `purchases`, `inventory_adjustment` → `inventory`) con etiqueta y módulo propietario. Agregar uno es un cambio de una línea. Sin origen: `source_type` nulo (p. ej. saldo inicial).
3. **Idempotencia**: restricción única parcial `(company_id, source_type, source_id, source_line, product_id, warehouse_id, kind)` cuando hay origen, más `unique(reverses_id)` cuando no es nulo. La fachada `record_movement` busca primero; si existe devuelve el mismo movimiento con `created=False` (reintento) o, si la cantidad difiere, falla con `MovementConflict('source_operation_mismatch')`. Si dos peticiones concurrentes pasan la búsqueda, la restricción rechaza a una (`IntegrityError`) y se resuelve releyendo el existente. Si la operación de origen ya fue revertida, repetirla devuelve el movimiento original (estado «revertido») con `created=False`: no se registra uno nuevo; reabrir la operación exige un documento de origen nuevo. `source_line` (texto, `''` por defecto) permite que un documento con varias líneas del mismo producto no choque.
4. **Saldo** = Σ entradas − Σ salidas sobre **todas** las filas del libro (el original revertido y su contramovimiento se anulan entre sí); `status` es solo etiqueta de trazabilidad. Nadie escribe el saldo: se calcula (`get_balance(company_id, product_id, warehouse_id)`).
5. **Salidas sin saldo suficiente** se rechazan (`insufficient_stock`) salvo `allow_negative=True`, decisión que cada productor futuro toma explícitamente. Para que dos salidas simultáneas no pasen ambas, `record_movement` bloquea la fila del almacén (`select_for_update`) dentro de la transacción, valida ahí que el almacén exista y esté activo, y `DeactivateWarehouse` toma el mismo bloqueo (así no queda saldo en un almacén que se desactiva).
6. **Validaciones al registrar**: el producto existe en la empresa y `tracks_stock=true`; la cantidad respeta `allows_fractions` de su unidad base; el almacén existe, es de la empresa y está activo. Los datos del producto salen de la nueva función de fachada `catalog.services.get_products_for_inventory(company_id, ids)` (DTO inmutable con nombre, `tracks_stock`, unidad). `inventory` la consume solo desde un adaptador de infraestructura; `ALLOWED_DEPENDENCIES['inventory'] = {'catalog'}` y `CONSUMERS` incluye `inventory`.
7. **Fachada pública** `inventory/services.py`: `record_movement`, `reverse_movement`, `get_balance`. Es lo único que Ventas/Compras/Ajustes llamarán; devuelve DTO, no entidades.
8. **Conexión de puertos**: `InventoryConfig.ready()` registra `stock_history.register(...)` (existe algún movimiento del producto en la empresa); el adaptador `WarehouseActivity` real calcula `has_nonzero_balance` desde el libro (`has_pending_receipts` sigue en «no» hasta la historia de recepciones).
9. **Lectura HTTP**: `GET /api/stock-movements/` (paginada, filtros) y `GET /api/stock-movements/<id>/`, solo lectura (sin POST/PATCH/DELETE → 405), `required_modules = ('inventory',)`, administrador de empresa. Cada origen incluye `available` = módulo propietario habilitado (`shared.module_gate`), para que la UI muestre el vínculo solo si procede.
10. **Índices**: `(company_id, occurred_at)`, `(company_id, product_id, warehouse_id)`.

## Alternativas consideradas
- **Saldo almacenado (`StockItem`) actualizado en cada movimiento:** más rápido de leer, pero introduce una segunda fuente de verdad y riesgo de desvío; descartada para el MVP (volumen bajo). Se puede añadir como caché derivada.
- **Evento de dominio / bus para que Ventas notifique:** infraestructura nueva sin necesidad (`CLAUDE.md`, fuera del MVP); se usa fachada.
- **Endpoint HTTP para crear movimientos:** no pedido (la UI es de solo lectura) y abriría una vía de escritura manual sin documento fuente; descartado.
- **Balance contando solo `status=confirmed`:** obligaría a tratar el contramovimiento como caso especial; el libro completo es más simple y auditable.

## Estrategia de rollback / mitigación
Migración aditiva `inventory/0002` (nueva tabla `inventory_stock_movement`); revertir = `migrate inventory 0001`. Sin productores hoy, la tabla queda vacía y el comportamiento observable no cambia salvo la UI nueva. Si el proveedor de historial causara bloqueos no deseados, basta no registrar el proveedor (una línea en `apps.py`); los datos no se alteran.

## Consecuencias
- Primer consumo de otro módulo por `inventory`: se actualizan el test de fronteras y `ddd.md` (mapa de dependencias, `StockMovement`).
- Con el primer movimiento, los productos afectados pasan a bloquear cambios de `tracks_stock`/unidad (AC-03 de PB-INV-001): comportamiento esperado.
- El saldo se calcula por agregación: si el volumen crece, se añade una tabla de saldos derivada sin cambiar el contrato.
- Quien registre movimientos desde otros módulos (ventas, compras) debe usar `inventory.services` y una clase de origen del catálogo.
