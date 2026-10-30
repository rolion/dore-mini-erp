# ADR-compras-borrador-crear-editar-modelo-compra-borrador: Agregado `Purchase` con líneas, importes derivados y persistencia

**Estado:** Propuesto
**Task relacionado:** TASK-compras-borrador-crear-editar
**Fecha:** 2026-10-29

## Contexto
PB-COM-002 introduce el segundo agregado de `purchases`: la compra con sus líneas. Debe guardar proveedor, fecha, referencia externa, notas e ítems, derivar subtotales/total, no tener impuestos ni descuentos, no mover stock ni crear gastos y conservar nombre y precio acordados de cada línea para cuando se confirme (task posterior). Referencia: `Order` de Ventas (`docs/adr/ADR-ciclo-pedido-entrega-cobro-modelo-dominio.md`). Impacto: tablas y migración nuevas, sin datos existentes.

## Decisión
1. **Agregado `Purchase`** (`purchases/domain/purchase.py`, dominio puro) con `id` UUID, `supplier_id`, `purchase_date`, `external_reference` (opcional, ≤ 100), `notes` (opcional, ≤ 2000), `status` (`PurchaseStatus`, hoy solo `DRAFT`), `items` y `created_at/updated_at`. Los totales **no se asignan**: `subtotal` de línea y `total` son propiedades derivadas. Sin campos de impuestos, descuentos ni costos adicionales.
2. **`PurchaseItem`**: `id`, `product_id`, `product_name` (snapshot), `unit_abbreviation` (snapshot, vacío si el producto no tiene unidad base), `quantity` `Decimal` (> 0, hasta 3 decimales, ≤ 99 999 999.999), `unit_price` `Decimal` (≥ 0, 2 decimales, `shared.domain.money.parse_money`). `subtotal = (quantity × unit_price)` redondeado a 2 decimales mitad hacia arriba (`ROUND_HALF_UP`); `total = Σ subtotales`; el total y cada subtotal deben caber en `MONEY_MAX` (12 dígitos). La moneda es BOB, única e implícita: no se guarda; la API expone `currency: "BOB"` como constante.
3. **Comportamiento por métodos del agregado** (nunca por asignación): `Purchase.create(...)`, `update_details(supplier_id, purchase_date, external_reference, notes)` y `replace_items(drafts)`. Ambas mutaciones llaman a `ensure_editable()` (solo `DRAFT`). `replace_items` valida **todas** las líneas y reúne los errores por posición antes de modificar nada: producto único por compra, máximo 200 líneas, cantidad y precio válidos. Un borrador puede tener cero líneas; exigir ≥ 1 es regla de Confirmar (otra task). El conjunto de líneas reemplaza al anterior; una línea cuyo `product_id` ya estaba en el borrador **conserva su snapshot** (`product_name`, `unit_abbreviation`); una línea nueva recibe el snapshot actual del catálogo.
4. **Reglas que dependen de otros agregados/módulos viven en la capa de aplicación** (`CreatePurchase`, `UpdatePurchase`): proveedor existente de la empresa y **activo** (repositorio de `Supplier`, mismo contexto), productos nuevos existentes y **activos**, y cantidad entera si la unidad base no admite fracciones (puerto `ProductCatalog` → ADR del contrato). Los errores de dominio y de aplicación se juntan en un solo `PurchaseValidationError` con forma `{campo: [msg], items: [{campo: [msg]}, …]}`.
5. **Persistencia**: `PurchaseModel` (`purchases_purchase`: `company_id` UUID indexado sin FK, `supplier_id` UUID sin FK, `purchase_date`, `external_reference`, `notes`, `status`, `total` `Decimal(12,2)` derivado que solo escribe el repositorio, timestamps; índices `(company_id, purchase_date)` y `(company_id, supplier_id)`) y `PurchaseItemModel` (`purchases_purchase_item`: FK a la compra con `on_delete=CASCADE` dentro del mismo agregado, `position`, `product_id` sin FK, snapshots, `quantity` `Decimal(12,3)`, `unit_price` `Decimal(12,2)`, `subtotal` `Decimal(12,2)` derivado). `DjangoPurchaseRepository(company_id)` filtra siempre por empresa, guarda el agregado y sus líneas en una transacción (`atomic` + `select_for_update` de la compra al editar; las líneas se reemplazan completas) y devuelve el agregado reconstruido por un mapper. Migración `0002_purchase` nueva.
6. **Orden y lectura**: listado por `purchase_date` descendente, `created_at` descendente, `id`; el repositorio ofrece `list(supplier_id=None)` paginable y resuelve los nombres de proveedor de una página en una consulta (mismo contexto, sin pasar por la fachada).
7. **Guardar no tiene efectos fuera de `purchases`**: el módulo no importa `inventory` ni `expenses`; una prueba comprueba que guardar o editar un borrador no crea movimientos de inventario ni gastos.

## Alternativas consideradas
- **Cantidad entera como Ventas**: descartada, las compras suelen ser por peso o volumen y el catálogo ya modela unidades que admiten fracciones; Inventario trabaja con 3 decimales, así que la cantidad comprada podrá recibirse sin conversión.
- **Total como columna editable o con `discount`/`tax` en cero**: descartada, el MVP no tiene impuestos ni descuentos; la ausencia de los campos evita que aparezcan como funcionales.
- **Referenciar el nombre del producto solo por `product_id` y leer el nombre del catálogo al mostrar**: descartada, el criterio exige conservar el nombre acordado; un renombrado no debe reescribir una compra.
- **Editar líneas una a una por API (`POST/PATCH/DELETE /items/`)**: descartada, el requerimiento es un formulario único con «Guardar borrador»; reemplazar el conjunto es atómico y más simple.
- **Líneas duplicadas por producto**: descartada por coherencia con Ventas y para que el snapshot por `product_id` sea inequívoco.
- **Control optimista (`If-Match`/`updated_at`)**: descartado en este MVP; se mitiga con guardado atómico y bloqueo de fila.

## Estrategia de rollback / mitigación
Cambio aditivo: dos tablas nuevas sin datos previos. Rollback = revertir el PR; si la migración se aplicó, `migrate purchases 0001` las elimina (nada más las referencia). El módulo está deshabilitado por defecto. Mitigación de redondeo: reglas implementadas una sola vez en el dominio, con pruebas de casos límite, y replicadas en una función pura del frontend con las mismas pruebas.

## Consecuencias
- La task de confirmación podrá congelar el agregado añadiendo estados a `PurchaseStatus` y transiciones por método; las líneas (con snapshots) ya estarán listas.
- Los ids de línea cambian entre guardados de un borrador; ningún otro dato los referencia mientras sea borrador.
- Quedan fuera: numeración de compras, adjuntos, pagos, recepción de mercadería.
