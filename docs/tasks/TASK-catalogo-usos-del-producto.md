# TASK-catalogo-usos-del-producto: Distinguir insumos, intermedios y productos vendibles (PB-CAT-001)

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-catalogo-usos-del-producto
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/29

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-29 | (nuevo) → INVESTIGATION | Task creado; rama desde `origin/main` al día | delivery-start |
| 2026-10-29 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | Cambia el modelo del producto (migración de datos), el contrato API y la frontera Catalog → Sales/Purchases | delivery-start |
| 2026-10-29 | PLANNING → ENGINEERING | Specification READY (sin decisiones de negocio abiertas) | delivery-start |
| 2026-10-29 | ENGINEERING → REVIEW | Implementación completa según plan v1; pruebas con PostgreSQL pendientes de correr (ver Implementación) | delivery-build |

## Investigación

### Requerimiento
**PB-CAT-001 · Distinguir insumos, productos intermedios y productos vendibles** (Catálogo, P1, dep. PB-INV-001). Como administrador, quiero distinguir qué ítems compro, produzco y vendo para que el mismo catálogo sirva a fabricantes, revendedores y negocios mixtos.

- Menú y vistas: Catálogo → Productos; ampliar listado y alta/edición con una sección «Usos del producto».
- Campos: nombre, categoría operativa (materia prima, empaque, intermedio, terminado, mercadería), se puede comprar, se puede vender, controla stock, unidad base, estado. Precio de venta obligatorio solo si se puede vender; el precio de compra se captura en cada compra.
- Filtros: buscar por nombre; filtrar por uso, categoría y estado. Guardar y desactivar conservan referencias históricas; ningún cambio convierte automáticamente un producto en otro.
- AC: Compras solo permite productos activos comprables; Ventas solo activos vendibles, validado también en API. Dore compra queso y bolsas vacías, produce cuñapés intermedios no vendibles y vende bolsas de seis; la librería compra y vende el mismo cuaderno. La categoría organiza y filtra, no impone usos exclusivos. No migrar todo a comprable ni cambiar stock/unidad histórica. La migración conserva como vendibles los productos actuales y exige revisar comprables y clasificación; los documentos históricos conservan sus snapshots.

### Hechos encontrados
- `backend/modules/catalog/domain/product.py:55-67` — `Product` solo tiene `name`, `description`, `sale_price` (obligatorio), `active`, `tracks_stock`, `base_unit`. No existe categoría ni distinción comprable/vendible.
- `backend/modules/catalog/infrastructure/django/models.py:27-39` — `ProductModel.sale_price` es `NOT NULL` (12,2). Última migración del módulo: `0003_stock_units_warehouses.py`.
- `backend/modules/catalog/domain/product.py:70-97` — `Product.create` valida nombre y precio; los cambios se hacen por métodos del agregado (`rename`, `change_price`, `configure_stock`, `activate`/`deactivate`).
- `backend/modules/catalog/application/commands.py:58-105` — `CreateProduct`/`UpdateProduct` reciben `sale_price`; `StockControl.apply` (`:19-55`) gobierna `tracks_stock`/unidad con bloqueo por historial (`StockHistoryLocked`).
- `backend/modules/catalog/api/serializers.py:8-35` y `api/views.py:64-79` — contrato actual; la lista filtra `search`, `active`, `tracks_stock` (`views.py:66-70`, `infrastructure/django/repositories.py:54-63`).
- `backend/modules/catalog/services.py:14-30` — fachada `get_product_for_sale` → `ProductForSale(id, name, sale_price, active)`; «la regla de producto activo la aplica quien vende».
- `backend/modules/sales/application/commands.py:82-105` — `AddOrderItem` solo rechaza producto inexistente o inactivo y toma snapshot de nombre y precio. Los ítems guardan su propio `product_name` (`sales/infrastructure/django/models.py:44`).
- `backend/modules/sales/infrastructure/adapters.py:42-48` y `sales/application/ports.py:13-29` — `ProductInfo`/`ProductCatalogAdapter`, único punto de Sales que conoce Catalog.
- `backend/modules/purchases/` — solo contiene **proveedores** (`domain/supplier.py`, `0001_initial.py`); no existe todavía ningún documento de compra, así que hoy no hay dónde elegir productos comprables.
- `frontend/panel_admin/src/app/features/products/` — lista (`product-list.component.html:40-45` filtro de estado, `:65-69` columna Precio), formulario (`product-form.component.ts:34-40`, `product-form.component.html:46-58` precio obligatorio, bloque «Inventario» condicionado por módulo `:60-100`), detalle y `products-api.service.ts`.
- `frontend/panel_admin/src/app/features/sales/components/order-items/order-items.component.ts:109` — el selector de productos del pedido llama `list({ search, active: true })`.
- `docs/design/design-system.md:109-141` — plantillas de lista, formulario, detalle y «sección condicionada por módulo en un formulario».

### Hipótesis / supuestos no confirmados
- El único consumidor de la API de productos es el panel Angular, por lo que exigir categoría al crear es aceptable.
- «Producir» no tiene módulo (Producción está fuera del MVP, `CLAUDE.md`): el intermedio es solo una clasificación, ni comprable ni vendible.

### Módulos y dependencias relacionadas
Catalog (dueño del cambio), Sales (consume `get_product_for_sale`), Purchases (consumirá una fachada nueva; hoy sin compras), Inventory (usa `tracks_stock`, no cambia). Reporting no lee productos.

### Implementaciones similares existentes
`tracks_stock`/`base_unit` (`StockControl`, `ADR-inventario-stock-almacenes-unidades-propiedad-y-fronteras`): campo nuevo con default conservador, migración que no toca datos existentes, regla en dominio y expuesta por fachada.

### Comportamiento actual
Todo producto activo es vendible y tiene precio obligatorio; no hay forma de registrar insumos o intermedios sin inventarles un precio ni de impedir que se vendan.

### Restricciones
`CLAUDE.md`: dinero en `Decimal`, no editar migraciones aplicadas, aislamiento por `company_id`, módulos solo se hablan por `services.py`, dominio sin Django, cambios de estado por métodos del agregado.

### Riesgos identificados
- `sale_price` nullable afecta a quien asuma precio presente (serializer, frontend `salePrice: string`, tests). Mitigado con la invariante «vendible ⇒ precio».
- Los productos existentes quedan «por revisar»: la UI lo hace visible sin bloquear su venta.
- El AC de Compras no es verificable de punta a punta sin documento de compra: se cubre con la fachada y su prueba.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — migración sobre `catalog_product`, cambio de contrato API que consume Angular y regla nueva que cruza Catalog → Sales (y Purchases a futuro).

### Diseño requerido
**SI** — se amplían formulario y lista con una sección nueva y filtros adicionales.

## Diseño
Ver `docs/design/DDR-catalogo-usos-del-producto-seccion-usos-y-filtros.md`.

## Arquitectura
Ver `docs/adr/ADR-catalogo-usos-del-producto-modelo-migracion-y-contrato.md`.

## Plan
`docs/plans/PLAN-2026-10-29-catalogo-usos-del-producto.md` (v1, COMPLETO).

## Implementación

**Resumen.** `Product` gana `category`, `can_buy`, `can_sell` y `sale_price` opcional (métodos `classify`/`set_uses`, INV-01..05); migración `0004_product_uses` (reversible); filtros `can_buy`/`can_sell`/`category` en repositorio y API (API-01..03); fachada `ProductForSale.can_sell` y `get_product_for_purchase` (API-05); `AddOrderItem` rechaza productos no vendibles (AC-01, API-04); UI según el DDR (UI-01..06).

**Cobertura.** AC-01: `sales/tests/test_api.py` · AC-02/EDGE-05: `catalog/tests/test_uses_api.py::ProductFacadeTests` · AC-03/04/05: `test_uses.py` + `test_uses_api.py` · AC-06: `ProductUsesMigrationTests` · AC-07/EDGE-06: `sales/tests/test_api.py` · AC-08: `test_uses.py`, `test_uses_api.py`, specs de `product-list` y `products-api.service` · AC-09: specs de `product-form` y `product-detail` · AC-10: spec de `order-items`.

**Pantalla de referencia / compartidos.** Se siguió `product-form` (sección condicionada) y `product-list` del sistema de diseño; no se crearon componentes compartidos nuevos (badges `badge-outline`).

**Estado de las pruebas (corrida propia, no es el Quality Gate).**
- Backend con PostgreSQL: `python manage.py test` → 962 pruebas OK (incluye migración 0003→0004 y reversa). Se observó una intermitencia preexistente en `sales.tests.test_repository.test_item_order_is_preserved` (orden de ítems), reproducida también sin estos cambios; y dos pruebas de `modularity` fallaron una vez por orden/concurrencia y no se repitieron.
- Frontend: Karma de `features/products` + `order-items` → 70 pruebas OK (se excluyó `app.component.spec.ts`, roto en `main` por `app.title`).

**Desviaciones respecto al plan.** Ninguna de alcance. Detalles: `Product.change_price` delega en `set_uses`; los fakes y fixtures de tests existentes recibieron `category`.

**Deuda técnica.** `app.component.spec.ts` roto en `main` (preexistente). No hay endpoint de compras que aplique `can_buy` (fuera de alcance).

## Review
_Pendiente_

## Publicación
_Pendiente_
