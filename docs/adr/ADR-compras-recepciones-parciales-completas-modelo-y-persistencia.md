# ADR-compras-recepciones-parciales-completas-modelo-y-persistencia: Agregado Recepción, acumulado por línea y estado de recepción

**Estado:** Propuesto
**Task relacionado:** TASK-compras-recepciones-parciales-completas
**Fecha:** 2026-10-30

## Contexto
PB-COM-004 introduce las recepciones de una compra confirmada: varias por compra, con fecha y cantidades por línea, sin superar lo comprado. `Purchase.reception_status` existe como atributo preparatorio sin escritor (ADR confirmar-cancelar, decisión 6) y la cancelación ya se bloquea con actividad. Hay que decidir quién es el agregado, dónde viven las cantidades recibidas y cómo se calcula el estado de recepción sin romper la regla de que el estado solo cambia por métodos del agregado.

## Decisión
1. **Nuevo agregado `Receipt`** (`purchases/domain/receipt.py`), distinto de `Purchase`: `id`, `purchase_id`, `receipt_date`, `status` (`ReceiptStatus`: `confirmed`, `reverted`), `warehouse_id | None`, `user_id`, `user_name`, `created_at`, y `lines: list[ReceiptLine]` (`purchase_item_id`, `product_id`, `product_name`, `unit_abbreviation`, `quantity`). Es inmutable tras crearse; `reverted` existe en el contrato pero ninguna acción de esta task lo produce (H-03). Referencia derivada `REC-` + 8 hex del id (H-01).
2. **La compra decide si puede recibir y qué estado resulta**, por un método del agregado: `Purchase.receive(receipt_id, receipt_date, today, received_before, drafts, ...) -> Receipt`. Exige `status == confirmed` (si no, `PurchaseNotReceivable`), valida todas las líneas y junta los errores por posición, y después recalcula `reception_status`. Quien llama (aplicación) aporta `received_before`: el acumulado confirmado por `purchase_item_id` que lee del repositorio de recepciones bajo el bloqueo de la compra. El dominio no consulta ninguna base.
3. **Reglas de `receive`** (INV): fecha obligatoria, válida y no futura; ≥ 1 línea; cada línea referencia una línea de la compra y no se repite; cantidad `Decimal` > 0 con 3 decimales como máximo (`validate_quantity`, entera si la unidad no admite fracciones); `received_before[item] + cantidad ≤ item.quantity` (el mensaje indica el pendiente). Cantidad 0, negativa o excedida no se acepta (H-08).
4. **Estado derivado y único escritor.** `reception_status` se recalcula en `receive` con el acumulado nuevo: todas las líneas con acumulado ≥ comprado → `received`; alguna con acumulado > 0 → `partial`; si no, `not_received`. No depende de `payment_status`. Como `has_activity` ya considera `reception_status`, la cancelación queda bloqueada desde la primera recepción sin cambiar la regla existente.
5. **`allowed_actions`** suma `receive` cuando la compra está `confirmed` y `reception_status != received`. El detalle de la compra expone por línea `received_quantity` y `pending_quantity` (calculados por la aplicación desde el acumulado; la compra los recibe como dato, no los persiste).
6. **Persistencia.** Dos tablas nuevas, migración **`0004_receipts`** (aditiva): `purchases_receipt` (`id`, `company_id` indexado, `purchase_id` UUID **sin FK** hacia `purchases_purchase`, `receipt_date`, `status`, `warehouse_id` UUID null, `user_id` UUID null, `user_name`, `created_at`; índice `(company_id, purchase_id)`) y `purchases_receipt_item` (`receipt` FK con cascade, `position`, `purchase_item_id` UUID **sin FK**, `product_id`, `product_name`, `unit_abbreviation`, `quantity` Decimal(12,3)). Sin FK hacia la línea de la compra porque `DjangoPurchaseRepository.save` borra y recrea las líneas (conserva el `id`, no la fila). El acumulado se obtiene con una agregación (`SUM(quantity)` por `purchase_item_id`, solo recepciones `confirmed`, de la empresa).
7. **Repositorio** `ReceiptRepository(company_id)`: `get(receipt_id)`, `list_for_purchase(purchase_id)`, `received_totals(purchase_id) -> dict[UUID, Decimal]`, `save(receipt)`. Filtra siempre por `company_id`. Las recepciones de una compra se serializan por el bloqueo `select_for_update` de la fila de la compra (la aplicación siempre bloquea la compra primero).
8. **Sin cambios en `Purchase.cancel`/`has_activity`**; la regla INV-05 de PB-COM-003 pasa a ser alcanzable por primera vez y tiene pruebas de API sin manipular el estado.

## Alternativas consideradas
- **Recepciones como hijas del agregado `Purchase`** (lista dentro de la compra): la compra reescribe sus líneas al guardar y cargaría todas las recepciones en cada operación (cancelar, confirmar, listar). Descartada; un agregado propio con el acumulado leído bajo el bloqueo de la compra mantiene la invariante con una agregación barata.
- **Guardar `received_quantity` en la línea de la compra** (columna): duplica una cifra derivable y puede divergir de las recepciones; la reversa futura (H-03) obligaría a mantenerla. Descartada; se deriva por agregación.
- **FK a `PurchaseItemModel`:** descartada por el borrado y recreado de líneas en `save`; se usa UUID con la misma convención que el resto de referencias (`supplier_id`, `product_id`).
- **Que `Receipt.create` valide contra la compra sin pasar por `Purchase`:** descartada; el estado de la compra y su `reception_status` solo cambian por un método del agregado `Purchase`.
- **Recalcular `reception_status` al vuelo (sin persistirlo):** descartada; ya existe la columna, la lista y la cancelación la leen, y una consulta por compra en la lista sería innecesaria.

## Estrategia de rollback / mitigación
Migración aditiva (dos tablas nuevas): `migrate purchases 0003` las elimina, perdiendo las recepciones registradas (aceptable antes de producción). `purchases_purchase.reception_status` quedaría en `partial/received` para compras con recepciones; antes de revertir la migración en un entorno con datos hay que devolverlo a `not_received`. Si una recepción se registró por error no hay «deshacer» en esta task (H-03); la corrección es una reversa futura o un ajuste de inventario. Todas las reglas están cubiertas por pruebas de dominio, aplicación y API.

## Consecuencias
- `Purchase` suma `receive()`, `ReceiptStatus`, `PurchaseNotReceivable`; la reversa futura de una recepción deberá recalcular `reception_status` con el mismo cálculo (se extrae a una función del dominio reutilizable).
- La lista de compras no cambia; el detalle suma campos aditivos.
- `purchase_item_id` es una referencia por UUID: si algún día las líneas de una compra confirmada se editaran, habría que revisar esa referencia (hoy no son editables).
