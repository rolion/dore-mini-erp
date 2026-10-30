# ADR-inventario-revertir-movimientos-contramovimientos: Reversión de movimientos y de recepciones

**Estado:** Propuesto
**Task relacionado:** TASK-inventario-revertir-movimientos
**Fecha:** 2026-10-30

## Contexto
El libro de movimientos es inmutable: lo único que cambia es `confirmed → reversed` y la corrección es un contramovimiento vinculado (`StockMovement.reverse`, `ReverseMovement`). Falta exponerlo con reglas de negocio: motivo obligatorio, orígenes permitidos y la reversión de una recepción de Compras, que cruza dos módulos y debe ser todo-o-nada. `ReceiptStatus.REVERTED` ya existe pero nada lo usa.

## Decisión

**1. Inventario: reversión manual por movimiento.**
- `POST /api/inventory/movements/<id>/reverse/` con `{ "reason": "<1..200 caracteres>" }` → `200` con el contramovimiento (misma representación de detalle). Módulo requerido: `inventory`.
- Orígenes permitidos: sin origen (manual), `inventory_adjustment` y `inventory_opening`. Rechazos `409` con `code`: `requires_return` (`sales_order`: «requiere una devolución, fuera de alcance»), `reverse_from_origin` (`purchase_receipt`: «corrígelo desde la recepción en Compras»), `already_reversed`, `cannot_reverse_reversal`, `insufficient_stock` (con producto, almacén y saldo vía `InsufficientStockConflict`). `404` si el movimiento no es de la empresa. `400` por motivo vacío o largo.
- La restricción por origen vive en el caso de uso (`ReverseMovement` recibe el conjunto de orígenes permitidos; el endpoint pasa los manuales), no en el agregado: el agregado sigue sabiendo revertir cualquier movimiento, y la regla «de dónde se corrige» es política de aplicación.
- `StockMovement.reverse` exige motivo no vacío (≤200). El texto por defecto desaparece.
- El detalle de movimiento añade `reversal`: `{ "allowed": bool, "code": str|null, "message": str|null }` (para que la UI explique por qué no hay botón) y expande `reversed_by` a `{id, reference, occurred_at, user: {id,name}, reason}` (conserva `id`, retrocompatible).

**2. Inventario: reversión de todos los movimientos de un documento (puerto para Compras).**
- Nueva función de fachada `reverse_source_movements(company_id, source_type, source_id, *, user_id, user_name, reason)` y caso de uso `ReverseSourceMovements`: toma el bloqueo de los almacenes implicados (en orden de id), revalida la política de stock negativo **sumando por producto y almacén**, y o bien inserta todos los contramovimientos y marca todos los originales, o lanza `InsufficientStock` con `shortages` completas sin cambiar nada. Idempotente por documento: si no queda ningún movimiento `confirmed` del origen, no hace nada y devuelve lista vacía.
- Esta ruta no aplica la restricción de origen del punto 1: quien la invoca (Compras) es el dueño del documento.
- `SourceMovement` (fachada) añade `status` y `reversed_by_id` para que el detalle de recepción muestre el vínculo.

**3. Compras: revertir una recepción.**
- `POST /api/purchases/<purchase_id>/receipts/<receipt_id>/revert/` con `{ "reason": "<1..200>" }` → `200` con el detalle de la recepción (ahora `reverted`). Módulo requerido: `purchases`.
- `Receipt.revert(reason, user_id, user_name, now)` es el único cambio de estado (`confirmed → reverted`); falla con `ReceiptAlreadyReverted` (`409 already_reverted`). `Purchase.recompute_reception(received_totals)` recalcula `reception_status` con las recepciones que siguen `confirmed` (el pendiente se restituye y `can_receive` vuelve a ser verdadero). No se toca ningún pago ni `payment_status` (INV: revertir una recepción no devuelve pagos).
- Nuevo caso de uso `RevertReception`: bloquea la compra (`for_update`, igual que `RegisterReception`), carga la recepción, y según su modo: `inventory` (o modo desconocido con `warehouse_id`) llama al puerto `StockEntry.reverse_entries(receipt_id, reason, actor)` — la compra se bloquea antes que el almacén, el mismo orden que al recibir —; `documental` no toca Inventario; `inventory` con módulo deshabilitado → `409 inventory_unavailable`. Si Inventario lanza `InsufficientStock`, el adaptador lo traduce a `StockShortageError` de Compras y el endpoint responde `409 insufficient_stock` con las líneas (producto, almacén, solicitado, disponible); la recepción sigue `confirmed`. Todo ocurre en la transacción de la petición.
- Migración aditiva `purchases/0007_receipt_reversal`: `reverted_at` (null), `reverted_by_user_id` (null), `reverted_by_name` (blank), `revert_reason` (blank, 200). Sin backfill: las recepciones existentes siguen `confirmed`.
- El detalle de recepción añade `reversal` (`{reverted_at, user_name, reason}` o `null`), `can_revert` (confirmada) y, por movimiento, `status` y `reversed_by` (id y referencia). El resumen en lista ya trae `status`.

**4. Permisos.** Sin cambios: el permiso por defecto (admin de la empresa) cubre ambos endpoints; el frontend solo oculta el botón, la barrera es el backend. Aislamiento por `company_id` en todos los repositorios; ids de otra empresa → 404.

**5. Idempotencia y concurrencia.** No hay clave de idempotencia de cliente: la segunda ejecución es `409` por diseño (la tarjeta exige que no pueda ejecutarse dos veces). `inv_mov_one_reversal_uniq` y el bloqueo de la compra/almacén garantizan un único ganador.

## Alternativas consideradas
- **Un solo endpoint genérico `reverse` que acepte cualquier origen y que Compras llame para su documento:** descartado; permitiría corregir ventas/compras desde una edición aislada de inventario, contra el criterio 2 de la tarjeta.
- **Que Compras llame a `reverse_movement` en bucle por línea:** descartado; no es todo-o-nada con política de stock (la línea 2 podría fallar tras revertir la 1) y bloquea el almacén varias veces. Se compensaría con deshacer manual, más frágil que una sola sección crítica.
- **Reversión parcial de recepción:** fuera de alcance por la tarjeta.
- **Modelar la reversión de la recepción como evento asíncrono entre módulos:** descartado (event sourcing/colas fuera del MVP, `CLAUDE.md`); la fachada síncrona en la misma transacción ya es el patrón de la recepción.
- **Guardar el motivo de la reversión de recepción solo en el movimiento:** descartado; la recepción documental no tiene movimiento y el documento debe ser autosuficiente.

## Estrategia de rollback / mitigación
- Migración aditiva y nullable: revertirla (`migrate purchases 0006`) solo borra columnas nuevas; los datos de recepciones previas no cambian. Si ya hay recepciones `reverted`, el rollback de código debe conservar el estado: tras desplegar, los contramovimientos y el estado `reverted` son datos válidos del libro y no se borran.
- Los endpoints nuevos son aditivos; quitar el botón de la UI y las rutas desactiva la función sin afectar lo existente.
- La transacción única evita estados intermedios (libro revertido con recepción confirmada o a la inversa); en caso de duda se compara el libro con las recepciones `reverted` (consulta de verificación en el PLAN).

## Consecuencias
- Hacer obligatorio el motivo en el dominio cambia tests existentes de INV-07 (se actualizan en la task).
- Inventario conoce el vocabulario «orígenes manuales»; añadir otro origen manual futuro exige tocarlo.
- El movimiento de una compra no enlaza a la recepción desde Inventario (falta el id de compra); se muestra el texto «corrígelo desde Compras». Deuda aceptada.
- Las devoluciones de ventas y de pagos de compras siguen sin existir; la UI lo dice explícitamente.
