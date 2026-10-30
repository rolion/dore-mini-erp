# ADR-catalogo-usos-del-producto-modelo-migracion-y-contrato: Usos del producto (categoría, comprable, vendible)

**Estado:** Propuesto
**Task relacionado:** TASK-catalogo-usos-del-producto
**Fecha:** 2026-10-29

## Contexto
Catalog modela todo producto como vendible con precio obligatorio. PB-CAT-001 exige distinguir insumos, intermedios y vendibles sin separar catálogos, y que Ventas (y Compras a futuro) validen el uso también en API. Hay datos reales en `catalog_product` cuyo stock y unidad no deben cambiar.

## Decisión
1. **Modelo.** `Product` gana tres atributos independientes: `category` (`raw_material`, `packaging`, `intermediate`, `finished`, `merchandise`; `null` solo en productos migrados «sin clasificar»), `can_buy` y `can_sell`. Ninguno depende de otro ni de `tracks_stock`; no hay combinación prohibida (ni siquiera «ni comprable ni vendible», p. ej. el cuñapé intermedio). La categoría solo organiza y filtra.
2. **Precio.** `sale_price` pasa a admitir `NULL` en BD y dominio; invariante `can_sell ⇒ sale_price` presente y ≥ 0. Si `can_sell` es falso el precio es opcional y, si existe, se conserva (no se borra al dejar de vender).
3. **Métodos del agregado.** `Product.classify(category)` y `Product.set_uses(can_buy, can_sell, sale_price)` validan las invariantes; no hay asignación directa. Cambiar usos o categoría no toca `tracks_stock`, unidad ni `active`, y no está sujeto al bloqueo por historial de stock.
4. **Migración `0004`** (nueva; no se editan las anteriores): `category` nullable, `can_buy` default `False`, `can_sell` default `True`, `sale_price` nullable. Sobre filas existentes: vendibles, no comprables, sin clasificar. `needs_review` es derivado (`category is null`), sin columna extra. Ninguna fila se reescribe con lógica: stock, unidad y pedidos históricos quedan intactos.
5. **Contrato API (`/api/products/`).** La respuesta añade `category`, `can_buy`, `can_sell`, `needs_review`; `sale_price` puede ser `null`. Entrada: `category` obligatoria al crear y nunca `null`, `can_buy` (omitido ⇒ `false`), `can_sell` (omitido ⇒ `true`), `sale_price` obligatorio si el resultado es vendible. Filtros nuevos: `can_buy`, `can_sell`, `category` (valor del enum o `unclassified`).
6. **Frontera entre módulos.** `ProductForSale` añade `can_sell`; `AddOrderItem` rechaza (400, campo `product_id`) producto inactivo o no vendible. Nueva fachada `get_product_for_purchase(company_id, product_id) -> ProductForPurchase(id, name, active, can_buy)` para el módulo de compras futuro, que aplicará «activo y comprable». La regla la aplica el consumidor; Catalog solo informa.
7. **Históricos.** Los pedidos conservan sus snapshots; cambiar usos o desactivar no los altera y la entrega de un pedido existente no revalida `can_sell`.

## Alternativas consideradas
- **Un campo `type` excluyente** (insumo / intermedio / vendible): rechazado; contradice «un negocio puede fabricar y revender» y el cuaderno comprado y vendido.
- **Categoría que deduce los usos** (mercadería ⇒ comprable y vendible): rechazado; convierte productos en otros automáticamente.
- **Backfill que infiera comprables** (p. ej. por movimientos de stock): rechazado; el AC prohíbe migrar automáticamente a comprables.
- **Columna `needs_review`**: rechazada por redundante.
- **`sale_price = 0` para no vendibles**: rechazado; mezcla «gratis» con «no aplica».

## Estrategia de rollback / mitigación
Migración aditiva y reversible: revertir `0004` rellena los `sale_price` nulos con `0.00` antes de volver a `NOT NULL` y elimina las columnas nuevas (solo se pierde la clasificación). Antes de desplegar, respaldar `catalog_product`. Los pedidos no se tocan. Desplegar backend antes que frontend.

## Consecuencias
- Los productos migrados aparecen «por revisar» hasta que el administrador los clasifique y marque los comprables; siguen vendiéndose normalmente.
- El contrato cambia (`sale_price` nullable, `category` obligatoria al crear); el único consumidor es el panel, que se actualiza en el mismo PR.
- «Compras solo permite comprables» queda garantizado por la fachada y su prueba; el endpoint de compras llegará con su propio task.
