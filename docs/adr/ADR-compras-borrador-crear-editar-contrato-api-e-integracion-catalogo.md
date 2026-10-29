# ADR-compras-borrador-crear-editar-contrato-api-e-integracion-catalogo: `/api/purchases/` y lectura de productos desde Catálogo

**Estado:** Propuesto
**Task relacionado:** TASK-compras-borrador-crear-editar
**Fecha:** 2026-10-29

## Contexto
Angular necesita un contrato para crear, editar, listar y consultar borradores, con errores por línea. Compras debe validar y copiar datos de productos del catálogo sin acoplarse a su infraestructura (`docs/architecture/ddd.md`; límites verificados en `sales/tests/test_boundaries.py`). El mapa de dependencias ya declara `purchases → catalog` (`modularity/domain/modules.py:23`), pero el test de límites aún lo prohíbe (`ALLOWED_DEPENDENCIES['purchases'] = set()`).

## Decisión
### API `/api/purchases/` (todas las vistas con `required_modules = ('purchases',)`)
- `GET /` lista paginada `{count,next,previous,results}` (`page`, `page_size` ≤ 100) con filtro `supplier_id=<uuid>` (UUID inválido → 400); resumen: `id, purchase_date, supplier {id,name}, external_reference, total, currency, status, items_count`.
- `POST /` crea el borrador (201) y devuelve el detalle. `GET /{id}/` detalle. `PATCH /{id}/` actualiza solo lo enviado; `items`, si viene, **reemplaza** todas las líneas. `PUT`/`DELETE` → 405 (no hay borrado en esta task). Sin tokens → 401; módulo deshabilitado → 403 `module_disabled`; otra empresa o inexistente → 404 `{"detail": "Compra no encontrada."}`.
- Entrada: `supplier_id` (obligatorio al crear), `purchase_date` (ISO `YYYY-MM-DD`, obligatoria al crear), `external_reference`, `notes`, `items: [{product_id, quantity, unit_price}]`. `quantity` y `unit_price` se aceptan como **string decimal o número JSON entero**; nunca float (el serializer usa `DecimalField` con `coerce_to_string` y rechaza notación científica). Campos desconocidos (`discount`, `tax`, `total`, `status`…) se **ignoran**: el total no se acepta del cliente.
- Salida (detalle): `id, supplier {id,name,active}, purchase_date, external_reference, notes, status ("draft"), currency ("BOB"), editable (bool), items [{id, product_id, product_name, unit_abbreviation, quantity, unit_price, subtotal}], total, created_at, updated_at`. Importes como strings con 2 decimales, cantidades con 3.
- Errores 400 con la forma `{campo: [msg]}` y, para líneas, `{"items": [{}, {"quantity": ["…"]}, {"product_id": ["…"]}]}` (un objeto por línea, vacío si la línea es válida) para que la UI marque el campo junto a su línea; se informan juntos los errores de cabecera y de todas las líneas, y no se persiste nada.
- Un borrador que ya no es editable responde 409 `{"detail": "La compra ya no admite cambios."}` (hoy inalcanzable: solo existe `draft`).
- El módulo `purchases` y `config/urls.py` montan `path('api/purchases/', include(…))` junto a `api/suppliers/`.

### Integración con Catálogo
- `catalog/services.py` agrega, junto a `ProductForSale` y `ProductForInventory`, el DTO inmutable `ProductForPurchase(id, name, active, unit_abbreviation, allows_fractions)` y la función `get_products_for_purchase(company_id, product_ids) -> dict[UUID, ProductForPurchase]` (una consulta con `select_related('base_unit')`; los ajenos o inexistentes no aparecen). No se reutiliza `get_products_for_inventory` para no atar la semántica de Compras a la de Inventario.
- `purchases/application/ports.py` define `ProductCatalog` (`get_products(product_ids)`) y los DTO propios; `purchases/infrastructure/adapters.py` implementa el adaptador sobre `catalog.services`. Es el **único** archivo de Compras que conoce a Catálogo.
- `test_boundaries.py`: `ALLOWED_DEPENDENCIES['purchases'] = {'catalog'}` y `CONSUMERS` incluye `purchases` (el acceso a otros módulos solo desde `adapters.py`).
- El selector de producto del frontend usa la API pública de Catálogo (`ProductsApiService`, `active=true`, `search`), como Ventas; el backend revalida todo.
- El proveedor se valida con el repositorio del propio contexto (`DjangoSupplierRepository`), no con la fachada `services.py`, que existe para otros módulos.

### Reglas de seguridad y aislamiento
Empresa siempre desde `shared/tenancy.company_id_from(request)`; `product_id` y `supplier_id` ajenos se tratan como inexistentes (error de campo, no 404 de la compra). Los ids de producto de una petición se consultan en lote.

## Alternativas consideradas
- **Anidar `/api/suppliers/{id}/purchases/`**: descartado, el filtro `supplier_id` cubre «Ver compras» con un solo recurso.
- **Rutas de línea independientes**: ver ADR del modelo.
- **Importar `catalog.domain`/modelos desde Compras**: prohibido por las reglas de módulos.
- **Que el frontend envíe nombre y unidad del producto**: descartado, el servidor es la fuente del snapshot; el cliente no debe poder fijar el nombre acordado.

## Estrategia de rollback / mitigación
Aditivo: nuevas rutas y una función nueva en la fachada de Catálogo (sin tocar las existentes). Rollback = revertir el PR; sin él, el frontend de Compras no existe. Compatibilidad hacia atrás: ningún contrato existente cambia (la única modificación visible es el nombre del ítem de menú y la ruta `purchases`, que deja de ser «Próximamente»).

## Consecuencias
- Compras queda acoplada a Catálogo solo por un puerto y su adaptador, igual que Ventas.
- Si Catálogo cambia `ProductForPurchase`, el único punto de ajuste es el adaptador.
- La task de confirmación reutilizará los snapshots y el puerto para validar de nuevo los productos.
