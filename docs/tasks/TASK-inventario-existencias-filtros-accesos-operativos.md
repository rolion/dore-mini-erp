# TASK-inventario-existencias-filtros-accesos-operativos: Ampliar consulta de existencias con filtros y accesos operativos (PB-INV-009)

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** SI
**Rama:** task/TASK-inventario-existencias-filtros-accesos-operativos
**Pull Request:** _sin abrir todavía_

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-29 | (nuevo) → INVESTIGATION | Task creado desde `origin/main` (c2eafb6) | delivery-start |
| 2026-10-29 | INVESTIGATION → PLANNING | Specification **BLOCKED**: la dependencia PB-CAT-001 no existía en el repo; decisión del usuario: detener hasta que se entregue | delivery-start |
| 2026-10-29 | PLANNING → DESIGN → PLANNING | PB-CAT-001 mergeado (PR #29, `a9dd1d4`); se actualiza `main`, se completa la investigación y se escribe el DDR | delivery-start |
| 2026-10-29 | PLANNING → ENGINEERING | Specification READY | delivery-start |
| 2026-10-29 | ENGINEERING → REVIEW | Implementación completa según plan v1; backend (inventory + catalog) 260 OK, frontend lint, build y Karma `features/inventory` 135/135 OK | delivery-build |

## Investigación

### Requerimiento
**PB-INV-009 · Ampliar consulta de existencias con filtros y accesos operativos** (Inventario, P2). Mejora posterior a PB-INV-005. Sobre `/inventory/stock`:
- Listado: agregar clasificación (materia prima, empaque, intermedio, terminado, mercadería) y etiquetas Comprable/Vendible (un producto puede tener ambos usos o ninguno).
- Filtros nuevos: clasificación y selectores independientes Comprable/Vendible (Todos/Sí/No); se combinan, se limpian con «Limpiar filtros» y se conservan al volver del detalle.
- Detalle: añadir clasificación y usos; mantener «Ver movimientos».
- «Registrar apertura» (solo sin movimientos previos, admin, Inventario activo) y «Registrar ajuste» (admin, Inventario activo, almacén activo) con producto/almacén preseleccionados; al terminar vuelven al mismo detalle con saldo e historial actualizados; cancelar vuelve sin cambios; elegibilidad de apertura revalidada al confirmar (UI, URL y API).
- Reutiliza formularios, permisos, idempotencia y concurrencia de PB-INV-003/006; sin endpoints nuevos de movimientos. Los datos de clasificación y usos proceden de Catálogo (PB-CAT-001): esta historia **no** crea otra clasificación.
- Fuera de alcance: cambiar PB-INV-005, movimientos libres, compras/producción, costeo, reservas, devoluciones, exportaciones.

### Hechos encontrados
- `backend/modules/catalog/infrastructure/django/models.py:29-46` — `ProductModel` solo tiene `name`, `description`, `sale_price`, `active`, `tracks_stock`, `base_unit`. **No hay clasificación ni usos comprable/vendible.**
- Búsqueda de `clasificaci|purchasable|sellable|comprable|vendible|PB-CAT-001` en todo el worktree (excluyendo `node_modules`): sin resultados. Tampoco aparecen (`git grep`) en `origin/task/TASK-catalogo-productos-mvp`; ninguna rama remota corresponde a PB-CAT-001 (`git branch -r`).
- `backend/modules/catalog/services.py:33-66` — `ProductForInventory` (`id, name, tracks_stock, unit_abbreviation, allows_fractions, active`) y `list_products_for_inventory(company_id, search, active)`: es el único punto por el que Inventario lee Catálogo; hoy no entrega clasificación ni usos.
- `backend/modules/inventory/application/movement_ports.py:7-24` y `infrastructure/adapters.py:13-29` — `ProductInfo`/`ProductDirectory.list_stock_products(search, active)` y su adaptador.
- `backend/modules/inventory/application/stock_use_cases.py:156-217` — `StockQuery` (`search`, `warehouse_id`, `active`, `balance`), `ListStock` (composición en memoria productos × almacenes, filtros de saldo en memoria) y `GetStockPosition` (`has_history`, `can_register_opening = product.active and warehouse.active and not has_history`).
- `backend/modules/inventory/api/stock_views.py:133-206` — `_stock_query` valida parámetros (400 por parámetro); `GET /api/stock/` y `GET /api/stock/<product_id>/<warehouse_id>/`.
- `backend/modules/inventory/api/stock_views.py:89-130` y `application/stock_use_cases.py:58-122` — `RegisterOpening` ya revalida bajo bloqueo del almacén (`_reject_history` → 409 `stock_history_exists`) e idempotencia por `opening_id`: la revalidación al confirmar existe.
- `frontend/panel_admin/src/app/features/inventory/pages/stock-list/stock-list.component.ts:29-145` — filtros `search`, `warehouseId`, `active`, `balance` en un `FormGroup`; estado **no** se conserva al ir al detalle (solo se lee `warehouse_id` de la query); ya hay botón «Ajustar» por fila (`stock-list.component.html:112-114`).
- `frontend/.../stock-detail/stock-detail.component.{ts,html}` — detalle con historial embebido; «Registrar apertura» enlaza con `?warehouse_id=` pero **no** preselecciona producto ni vuelve al detalle; **no hay** botón «Registrar ajuste» en el detalle; nota `openingNote` cubre solo «ya tiene movimientos / inactivo».
- `stock-opening.component.ts:314` y `adjustment-form.component.ts:80,293` — leen `warehouse_id` (apertura) y `product_id`/`warehouse_id` (ajuste) de la query; ninguno acepta un retorno al detalle (`returnUrl`).
- `docs/tasks/TASK-inventario-consultar-existencias-historial.md` — PB-INV-005 en PUBLISH; su deuda técnica (composición en memoria) aplica a los filtros nuevos.

### Actualización tras PB-CAT-001 (2026-10-29, `main` en `a9dd1d4`)
- `catalog/infrastructure/django/models.py` — `ProductModel.category` (nullable; `null` = sin clasificar/por revisar), `can_buy` (default False), `can_sell` (default True); migración `0004_product_uses.py`.
- `catalog/domain/product.py:48-51,75-83` — `CATEGORIES` (`raw_material, packaging, intermediate, finished, merchandise`), `needs_review`.
- `catalog/api/views.py:65-88` — la lista de productos ya filtra `category`, `can_buy`, `can_sell`.
- `catalog/services.py:35-87` — `ProductForPurchase`/`ProductForSale` con `can_buy`/`can_sell`, pero `ProductForInventory` y `list_products_for_inventory` **aún no** entregan categoría ni usos: se ampliarán en esta tarea (cambio aditivo en la fachada).
- `frontend/.../products/models/product.ts` — `ProductCategory`, `PRODUCT_CATEGORIES`, `categoryLabel` reutilizables.

### Hipótesis / supuestos (resueltos)
- (Resuelto) PB-CAT-001 definió el contrato descrito arriba. Decisión: los productos sin clasificar se filtran con «Sin clasificar». Antes de PB-CAT-001 se suponía que definirá clasificación (5 valores) y usos como atributos del producto en Catálogo, expuestos por `catalog.services`; su contrato exacto (nombres de valores, si es obligatoria, valores por defecto de productos existentes) es desconocido.
- «Administrador autorizado» = `CompanyAdminPermission` ya aplicado a los endpoints de stock; se asume sin permisos nuevos.
- La conservación de filtros al volver del detalle se puede resolver con query params o estado de navegación en el frontend (decisión de diseño, no de negocio).

### Módulos y dependencias relacionadas
`inventory` (existencias, apertura, ajustes), `catalog` (clasificación y usos, vía `services.py`), `modularity` (gate `inventory`), frontend `features/inventory`.

### Implementaciones similares existentes
`StockListComponent`/`MovementListComponent` (filtros con `FormGroup`), `StockDetailComponent`, flujos `stock-opening` y `adjustment-form`.

### Comportamiento actual
Existencias filtra por nombre, almacén, estado y saldo; el detalle ofrece «Ver movimientos» y «Registrar apertura» (condicionada); el ajuste solo se alcanza desde el botón por fila de la lista; ninguna operación vuelve al detalle.

### Restricciones
`company_id` en todo; sin migraciones propias de Inventario; entre módulos solo `services.py`; `Decimal`; no duplicar endpoints; no cambiar reglas de apertura/ajuste.

### Riesgos identificados
- **Dependencia inexistente (PB-CAT-001)** — bloqueante.
- Cambio de contrato de `GET /api/stock/` y `…/<product>/<warehouse>/` (campos nuevos, aditivo).
- Filtros adicionales en memoria sobre la composición productos × almacenes (volumen).

### Veredicto de complejidad
**NEEDS_PLAN** — extiende lectura y navegación existentes sin decisiones arquitectónicas nuevas, siempre que PB-CAT-001 provea los datos; plan COMPLETO por tocar la frontera Catalog↔Inventory y el contrato API.

### Diseño requerido
**SI** — filtros nuevos, etiquetas, acciones condicionadas y flujo de retorno de varios pasos.

## Diseño
`docs/design/DDR-inventario-existencias-filtros-accesos-operativos-filtros-detalle-y-retorno.md`

## Arquitectura
_No aplica según veredicto_

## Plan
`docs/plans/PLAN-2026-10-29-inventario-existencias-filtros-accesos-operativos.md` (v1, COMPLETO, READY). Pregunta abierta anterior resuelta: PB-CAT-001 ya está en `main`.

## Implementación
**Backend.** `catalog.services`: `ProductForInventory` con `category`, `can_buy`, `can_sell` y `list_products_for_inventory(category, can_buy, can_sell)` (`category='none'` = sin clasificar) (INV-05, AC-02, AC-03). `inventory`: `ProductInfo`/`ProductDirectory.list_stock_products` y adaptador; `StockQuery` y `ListStock` pasan los filtros a Catálogo; `StockPosition.can_register_adjustment` = almacén activo (INV-04); `api/stock_views.py` valida `category`, `can_buy`, `can_sell` (400 por parámetro, EDGE-03) y expone `category`, `can_buy`, `can_sell` en filas y detalle, y `can_register_adjustment` en el detalle (API-01, API-02). Sin migraciones ni endpoints nuevos; apertura y ajuste conservan sus endpoints y reglas (AC-04, AC-05; la revalidación de apertura al confirmar ya existía en `RegisterOpening`).
**Frontend** (`features/inventory`). `models/stock.ts` y `stock-api.service.ts` (campos y filtros); `services/stock-filters-state.ts` (filtros y página en memoria, AC-08); `services/stock-return.ts` (`return=stock` + ids UUID válidos → enlace al detalle, nunca una URL libre; EDGE-05). `stock-list`: columnas Clasificación y Usos, filtros Clasificación / Comprable / Vendible, «Limpiar filtros», estados vacío inicial, sin resultados con filtros, cargando y error con Reintentar (UI-01, AC-07). `stock-detail`: filas Clasificación y Usos, «Registrar apertura» y «Registrar ajuste» con producto, almacén y `return=stock`, notas de apertura/ajuste no disponibles (UI-02, AC-04, EDGE-06). `stock-opening` y `adjustment-form`: preselección de producto y retorno al detalle al guardar y al cancelar (UI-03, AC-05, AC-06). Docs: `design-system.md`, `modulos-implementados.md`.
**Pruebas.** Backend: `inventory/tests/test_stock_query.py` (filtros combinados, sin clasificar, aislamiento por empresa, 400, detalle con categoría/usos y `can_register_adjustment`), `catalog/tests/test_services.py` (DTO y filtros). Frontend: specs de `stock-api.service`, `stock-list`, `stock-detail`, `stock-return` (nueva) y bloques nuevos en `stock-opening` y `adjustment-form`. El 409 por historial en la apertura queda cubierto por la suite existente (`test_stock.py`).
**Pantallas de referencia:** `movement-list` / `stock-list` (Lista de solo lectura con filtros) y `stock-detail` (Detalle con historial embebido); reutiliza `badge-outline`, `categoryLabel` y `PRODUCT_CATEGORIES` de `features/products`; no se creó nada en `shared/`.
**Desviaciones respecto al plan:** (0) la preselección de producto en la apertura usa `product_id` aunque no venga `return=stock` (igual que el ajuste), para no atar la preselección al retorno; (1) el texto de la nota de apertura se amplió a «La apertura solo procede sin movimientos previos; …» según la historia. Ninguna otra.
**Deuda técnica:** la preselección depende de que el producto esté entre las primeras 50 opciones que carga `OpeningProductsService` (limitación heredada, REV-09 de PB-INV-005); el estado de filtros vive en memoria y se pierde al recargar (aceptado en el DDR); filtros de clasificación/uso en BD, pero saldo y almacén siguen en memoria (deuda de PB-INV-005); revisión visual en navegador pendiente.
**Verificación propia (no es el Quality Gate):** `manage.py test modules.inventory modules.catalog` 260 OK; `npm run lint` OK; `ng build` OK; Karma `features/inventory` 135/135 OK (con `app.component.spec.ts` apartado temporalmente por estar roto en `main`; restaurado). Entorno: con autorización del usuario se copió `backend/.env` del checkout principal (sin abrirlo; ignorado por git), se usó su `.venv` y se enlazó `node_modules`.

## Review
_Pendiente_

## Publicación
_Pendiente_
