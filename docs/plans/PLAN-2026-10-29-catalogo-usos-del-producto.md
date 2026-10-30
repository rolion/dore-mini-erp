# PLAN-2026-10-29-catalogo-usos-del-producto (v1)

**Task:** TASK-catalogo-usos-del-producto · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** `docs/design/DDR-catalogo-usos-del-producto-seccion-usos-y-filtros.md` · `docs/adr/ADR-catalogo-usos-del-producto-modelo-migracion-y-contrato.md`

## Objective
Que un mismo catálogo distinga lo que se compra, lo que se produce y lo que se vende: cada producto tiene categoría operativa y usos independientes (`can_buy`, `can_sell`), Ventas (y Compras vía fachada) validan el uso en el backend, y los productos existentes se conservan vendibles y quedan por revisar.

## Context
Resumen y hechos en `docs/tasks/TASK-catalogo-usos-del-producto.md`.

# Specification

## Domain context
Bounded context **Catalog** (dueño). Relacionados: **Sales** (valida vendible al agregar ítems), **Purchases** (consumirá la fachada de comprables; hoy solo proveedores), **Inventory** (sin cambios).

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Categoría operativa | Clasificación que organiza y filtra: materia prima, empaque, intermedio, terminado, mercadería | PB-CAT-001 |
| Se puede comprar (`can_buy`) | El producto puede ser elegido en una compra | PB-CAT-001 |
| Se puede vender (`can_sell`) | El producto puede agregarse a un pedido; exige precio de venta | PB-CAT-001 |
| Por revisar (`needs_review`) | Producto migrado sin categoría (`category` nulo) | ADR |
| Controla stock | Atributo existente (`tracks_stock`), independiente de los usos | `product.py:62` |

## Current behavior
Todo producto activo es vendible; precio obligatorio (`product.py:60`, `serializers.py:13`); `AddOrderItem` solo valida existencia y estado (`sales/application/commands.py:93-97`); no hay categoría ni comprable.

## Expected behavior
- Un producto tiene `category`, `can_buy`, `can_sell` editables de forma independiente; el precio de venta es obligatorio solo si `can_sell`.
- Ventas rechaza en API agregar productos inactivos o no vendibles; la fachada de Catalog informa `can_buy` para Compras.
- La lista filtra por búsqueda, estado, uso y categoría (incluida «por revisar»).
- Tras migrar, los productos existentes son vendibles, no comprables y sin clasificar, con stock, unidad y pedidos intactos.

## Domain rules / invariants
- **INV-01 (nueva)** `category` ∈ {raw_material, packaging, intermediate, finished, merchandise}; `null` solo para productos migrados; no se puede volver a `null` ni crear sin categoría.
- **INV-02 (nueva)** `can_sell ⇒ sale_price` presente, ≥ 0, 2 decimales (regla de precio existente).
- **INV-03 (nueva)** `category`, `can_buy`, `can_sell` y `tracks_stock` son independientes: ninguna combinación está prohibida (incluso ni comprable ni vendible).
- **INV-04 (nueva)** Cambiar categoría o usos no modifica `tracks_stock`, unidad base, `active` ni snapshots, ni aplica el bloqueo por historial de stock.
- **INV-05 (nueva)** Si `can_sell` pasa a falso el `sale_price` guardado se conserva.
- **INV-06 (nueva)** Solo un producto activo y vendible puede agregarse a un pedido; solo uno activo y comprable podrá agregarse a una compra (la regla la aplica el consumidor con el dato de la fachada).
- **INV-07 (existente)** Dinero en `Decimal`; aislamiento por `company_id`.

## Acceptance criteria
- **AC-01** Agregar a un pedido un producto inactivo o con `can_sell=false` responde 400 con error en `product_id`; uno activo y vendible se agrega con snapshot de nombre y precio.
- **AC-02** La fachada `get_product_for_purchase` devuelve `can_buy` y `active`; una compra solo debe aceptar `active and can_buy` (cubierto con prueba de la fachada; el endpoint de compras está fuera de este task).
- **AC-03** Se pueden registrar: queso (materia prima, compra), bolsas vacías (empaque, compra), cuñapé (intermedio, ni compra ni venta, sin precio), bolsa de seis (terminado, venta con precio) y cuaderno (mercadería, compra y venta).
- **AC-04** La categoría no restringe usos: cualquier categoría acepta cualquier combinación de `can_buy`/`can_sell`/`tracks_stock`.
- **AC-05** Precio de venta obligatorio solo si `can_sell`; si no es vendible puede omitirse (`null`); activar `can_sell` sin precio da 400 en `sale_price`.
- **AC-06** La migración deja los productos existentes con `can_sell=true`, `can_buy=false`, `category=null` (`needs_review=true`) sin alterar `tracks_stock`, unidad, precio ni pedidos.
- **AC-07** Desactivar o cambiar usos de un producto no altera pedidos existentes (ítems, snapshots) ni impide entregarlos.
- **AC-08** `GET /api/products/` filtra por `search`, `active`, `can_buy`, `can_sell` y `category` (incluye `unclassified`); la lista del panel ofrece filtros de estado, uso y categoría.
- **AC-09** El formulario muestra la sección «Usos del producto» (categoría obligatoria, interruptores comprar/vender, precio solo si se vende) y avisa cuando el producto está por revisar; el detalle muestra los nuevos datos.
- **AC-10** El selector de productos del pedido solo ofrece activos y vendibles.

## Edge cases / Error cases
- **EDGE-01** `category` inválida o `null` → 400 en `category`. Crear sin categoría → 400.
- **EDGE-02** PATCH que deja `can_sell=true` y `sale_price` nulo → 400 en `sale_price`.
- **EDGE-03** Producto sin categoría (migrado) editable: guardar sin tocar categoría falla solo desde el formulario (UI la exige); la API acepta PATCH parcial que no la incluya.
- **EDGE-04** `can_buy`/`can_sell` no booleanos → 400.
- **EDGE-05** Producto de otra empresa en `get_product_for_*` → `None`.
- **EDGE-06** Pedido existente cuyo producto dejó de ser vendible: se muestra y se entrega igual; solo se bloquea agregar ítems nuevos de ese producto.
- **EDGE-07** `category=unclassified` en el filtro devuelve solo `category` nulo.

## Authorization / permissions
Sin roles nuevos (solo admin). Todas las consultas filtran por `company_id`; el módulo `catalog` sigue exigiendo habilitación (`required_modules`).

## API contract
- **API-01** `GET/POST /api/products/` y `GET/PATCH /api/products/{id}/`: la respuesta añade `category` (string|null), `can_buy`, `can_sell`, `needs_review` (read-only); `sale_price` string|null.
- **API-02** Entrada: `category` (obligatoria en POST, enum, no nula), `can_buy` (default false), `can_sell` (default true), `sale_price` (obligatorio si resulta vendible). PATCH parcial.
- **API-03** `GET /api/products/` nuevos filtros `can_buy=true|false`, `can_sell=true|false`, `category=<enum>|unclassified`; valores inválidos → 400.
- **API-04** `POST` de ítems de pedido (existente): 400 `{"product_id": ["El producto no se puede vender."]}` cuando `can_sell=false`.
- **API-05** Fachada Python (no HTTP): `ProductForSale.can_sell`; `get_product_for_purchase(company_id, product_id) -> ProductForPurchase | None`.
- Compatibilidad: cambia el contrato (categoría obligatoria al crear, `sale_price` nullable); el panel se actualiza en el mismo PR.

## UI behavior
Derivado de `DDR-catalogo-usos-del-producto-seccion-usos-y-filtros` y `design-system.md` §5.
- **UI-01** Formulario: sección «Usos del producto» (plantilla Formulario + sección condicionada); precio visible solo con «Se puede vender».
- **UI-02** Aviso `alert-warning` en edición de producto por revisar.
- **UI-03** Lista: filtros Estado/Uso/Categoría, columnas Categoría y Uso, badge «Por revisar», precio «—» si no vendible.
- **UI-04** Detalle: filas Categoría, Se compra, Se vende.
- **UI-05** Selector de pedidos: `canSell=true` además de `active=true`.
- **UI-06** Errores del servidor por campo; estados cargando/vacío/error como §4.

## Non-functional requirements
Consultas de lista siguen paginadas y filtradas por `company_id`; sin N+1 nuevo.

## Out of scope
Documentos de compra y su endpoint (futuro), módulo de Producción/recetas, precio de compra en el producto, categorías personalizables, cambios en Inventario o Reportes, indicador visual en pedidos antiguos.

## Open questions
- Ninguna que bloquee. Supuesto registrado: los defaults de API para clientes que omiten flags son `can_sell=true`, `can_buy=false`.

# Test Specification

## Unit tests
Dominio `Product`: INV-01..INV-05, EDGE-01/02/04 (`catalog/tests/test_domain.py`). Casos de uso `CreateProduct`/`UpdateProduct` con los escenarios del AC-03.

## Integration tests
API (`catalog/tests/test_api.py`): contrato, filtros, validaciones, aislamiento por empresa. Sales: `AddOrderItem` por API con producto no vendible/inactivo. Fachada (`test_services.py`): `can_sell`, `get_product_for_purchase`. Migración: prueba con datos previos (estado de `0003` → `0004`) verificando AC-06.

## E2E (¿corresponde?)
**NO** — la cobertura de componentes (Karma) y API es suficiente; no es un flujo crítico transversal nuevo.

## Regression tests
Se actualizan las pruebas existentes de productos, pedidos e inventario que crean productos sin categoría; verifican que stock, unidad y entrega siguen igual (AC-07).

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | Integración API ventas + unit del comando `AddOrderItem` |
| AC-02 | Prueba de fachada `get_product_for_purchase` (activo/inactivo/comprable/ajeno) |
| AC-03 | Test de casos de uso/API con los cinco productos de ejemplo |
| AC-04 | Unit dominio: matriz categoría × usos × tracks_stock |
| AC-05 | Unit dominio + API (POST/PATCH sin precio) |
| AC-06 | Prueba de migración con filas previas |
| AC-07 | Integración: pedido con ítem de producto luego no vendible/desactivado se lee y entrega |
| AC-08 | API filtros + spec de `product-list` y `products-api.service` |
| AC-09 | Spec de `product-form` y `product-detail` |
| AC-10 | Spec de `order-items` (params del listado) |

# Implementation Plan

## Architecture considerations
Dominio sin Django; usos en el agregado `Product`; `application/commands.py` los aplica; Sales solo conoce Catalog por `services.py` y un adaptador. `needs_review` derivado.

## Proposed solution
Ver ADR. Resumen: tres campos nuevos + `sale_price` nullable, migración aditiva `0004`, métodos `classify`/`set_uses`, filtros en repositorio, fachada ampliada, validación en `AddOrderItem`, UI según DDR.

## Files/components affected
- **Backend:** `catalog/domain/product.py`, `domain/repositories.py`, `application/commands.py`, `application/queries.py`, `api/serializers.py`, `api/views.py`, `infrastructure/django/{models,mappers,repositories}.py`, `services.py`, `migrations/0004_product_uses.py`; `sales/application/{ports,commands}.py`, `sales/infrastructure/adapters.py`; tests de `catalog`, `sales`, `inventory` que crean productos.
- **Frontend:** `features/products/{models,services,pages/*,testing}`, `features/sales/components/order-items`.
- **Docs:** `docs/producto/modulos-implementados.md` (sección Catálogo).

## Implementation steps
1. Dominio: campos, enum de categoría, `classify`, `set_uses`, precio nullable (INV-01..05).
2. Persistencia: modelo, mapper, migración `0004` y prueba de migración (AC-06).
3. Casos de uso y repositorio: comandos con usos, filtros `can_buy`/`can_sell`/`category` (AC-03..05, AC-08).
4. API: serializers, filtros y validaciones (API-01..03).
5. Fachada Catalog y Sales: `can_sell`, `get_product_for_purchase`, validación en `AddOrderItem` (AC-01, AC-02, AC-07).
6. Frontend: modelos y servicio, formulario, lista, detalle, selector de pedidos (UI-01..06, AC-08..10).
7. Actualizar pruebas existentes y documentación de producto.

## Database / migrations
`0004_product_uses` en `catalog`: `AddField category` (null), `can_buy` (default False), `can_sell` (default True), `AlterField sale_price` (null=True). Reversa: `RunPython` que pone `0.00` en nulos antes de revertir `AlterField`. No se editan migraciones aplicadas.

## Risks
- `sale_price` nullable: revisar todos los consumidores (serializers, frontend, `ProductForSale.sale_price`); en Ventas un producto vendible siempre tiene precio.
- Tests existentes que crean productos sin categoría fallarán por contrato nuevo: actualizar fixtures.
- Desplegar backend antes que frontend.

## New dependencies
Ninguna.
