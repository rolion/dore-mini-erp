# PLAN-2026-10-29-compras-borrador-crear-editar (v1)

**Task:** TASK-compras-borrador-crear-editar · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** [DDR pantallas-compras](../design/DDR-compras-borrador-crear-editar-pantallas-compras.md) · [ADR modelo-compra-borrador](../adr/ADR-compras-borrador-crear-editar-modelo-compra-borrador.md) · [ADR contrato-api-e-integracion-catalogo](../adr/ADR-compras-borrador-crear-editar-contrato-api-e-integracion-catalogo.md)

> COMPLETO por los tres ejes: reglas de dominio y cálculo de dinero nuevas (eje 1), dependencia nueva `purchases → catalog` (eje 2) y contrato API + migración + ADR/DDR (eje 3).

## Objective
Permitir que un administrador con Compras habilitado cree, edite, liste y consulte compras en estado borrador (proveedor activo, fecha, referencia externa, notas y líneas de producto con cantidad y precio), con subtotales y total calculados, sin generar movimientos de inventario ni gastos.

## Context
Ver `docs/tasks/TASK-compras-borrador-crear-editar.md`. Verificado sobre `main` (`e7fa547`): PB-COM-001 (`Supplier`) integrado; no existe ninguna compra; Compras → «Inicio» es «Próximamente».

# Specification

## Domain context
**Bounded Context:** Purchases. **Relacionados:** Catalog (lectura de producto por fachada), Modularity (compuerta). No se toca Inventory ni Expenses.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Compra (`Purchase`) | Adquisición planificada a un proveedor, con líneas de producto | PB-COM-002 |
| Borrador (`draft`) | Compra editable que no mueve stock ni genera gasto | PB-COM-002 |
| Línea (`PurchaseItem`) | Producto, cantidad y precio unitario acordados | PB-COM-002 |
| Referencia externa (`external_reference`) | Número de factura, nota o pedido del proveedor, texto libre | PB-COM-002 |
| Fecha de compra (`purchase_date`) | Fecha de la adquisición (puede ser pasada o futura) | PB-COM-002 |
| Subtotal / Total | Cantidad × precio de la línea (2 decimales) / suma de subtotales | PB-COM-002 |
| Snapshot | Nombre (y unidad) del producto copiados a la línea | AC 3 |
| BOB | Moneda única y fija (boliviano), informativa | PB-COM-002 |

Inconsistencias declaradas: UI en español, API y dominio en inglés; la UI muestra «Bs» (`MoneyPipe`) y «BOB» como etiqueta de moneda.

## Current behavior
`/api/purchases/` no existe. `purchases` (frontend) abre «Próximamente» (`app.routes.ts:80-88`). Ver TASK.

## Expected behavior
Con el módulo `purchases` habilitado, la persona entra a Compras → Compras, ve las compras de su empresa (filtrables por proveedor), pulsa «Nueva compra», elige un proveedor activo, la fecha y agrega líneas; ve subtotal por línea y total mientras escribe; «Guardar borrador» crea la compra en estado `draft` y abre su detalle; desde el detalle puede «Editar» el mismo borrador (cambiar cabecera, agregar, quitar o modificar líneas). Nada de esto crea movimientos de inventario ni gastos.

## Domain rules / invariants
- INV-01: `supplier_id` obligatorio y debe ser un proveedor **activo** de la empresa al guardar (crear o editar).
- INV-02: `purchase_date` obligatoria, fecha válida.
- INV-03: `external_reference` opcional ≤ 100; `notes` opcional ≤ 2000; ambos recortados; `null`/ausente equivale a vacío.
- INV-04: cada línea: producto existente de la empresa; **activo si es nuevo en el borrador**; `quantity` > 0, ≤ 99 999 999.999, hasta 3 decimales; entera si la unidad base del producto no admite fracciones; `unit_price` ≥ 0, 2 decimales, ≤ `MONEY_MAX`; nunca `float`.
- INV-05: un producto aparece una sola vez por compra; máximo 200 líneas; cero líneas permitido en un borrador.
- INV-06: `subtotal = round_half_up(quantity × unit_price, 2)`; `total = Σ subtotales`; ambos derivados (no asignables, no aceptados del cliente) y ≤ `MONEY_MAX`.
- INV-07: no existen impuestos, descuentos ni costos adicionales (ni campos ni efecto si se envían).
- INV-08: snapshot `product_name` y `unit_abbreviation` se toma al agregar el producto y **se conserva** en ediciones posteriores del borrador mientras el producto siga en él; cambios del catálogo no lo alteran.
- INV-09: solo un `draft` es editable; el estado cambia solo por métodos del agregado (hoy no hay transiciones).
- INV-10: guardar un borrador no crea `StockMovement` ni `Expense`; `purchases` no importa `inventory` ni `expenses`.
- INV-11: toda consulta filtra por `company_id` del usuario autenticado; productos y proveedores de otra empresa son inexistentes.
- INV-12 (existente): dominio sin Django; dinero en `Decimal`.

## Acceptance criteria
- AC-01: `POST /api/purchases/` con proveedor activo, fecha e ítems válidos → 201, `status="draft"`, `currency="BOB"`, ítems con `product_name`, `unit_abbreviation`, `subtotal`, y `total` = Σ subtotales (criterios 1 y 2).
- AC-02: referencia externa y notas son opcionales; ausentes o `null` → `""`. Sin `items` o `items: []` crea un borrador vacío con total `0.00` (INV-05).
- AC-03: validación conjunta, nada se persiste: proveedor ausente/inexistente/ajeno/inactivo, fecha ausente o inválida, referencia > 100, notas > 2000 → 400 con error por campo; línea con producto inexistente/ajeno/inactivo (nuevo), cantidad ≤ 0 o > máximo o con > 3 decimales o no entera para unidad sin fracciones, precio < 0 o con > 2 decimales o > máximo, producto repetido o más de 200 líneas → 400 con `items: [{…}]` indexado por línea y los errores de cabecera juntos.
- AC-04: `quantity`/`unit_price` aceptan string decimal o entero JSON; un `float` JSON no entero, `NaN`/`Infinity`, exponente o texto no numérico → error de campo de su línea; nunca se redondea en silencio.
- AC-05: `discount`, `tax`, `total`, `status`, `subtotal` enviados en cuerpo o en una línea se ignoran: el total sigue siendo Σ cantidad × precio (criterio 2 / INV-07).
- AC-06: `GET /api/purchases/{id}/` devuelve el detalle del ADR (con `editable=true` y proveedor aunque esté inactivo); inexistente o de otra empresa → 404 `{"detail": "Compra no encontrada."}`.
- AC-07: `PATCH /api/purchases/{id}/` actualiza solo los campos enviados; con `items` reemplaza todas las líneas (quitar, agregar y modificar); los productos que ya estaban conservan `product_name`/`unit_abbreviation` aunque el catálogo los haya renombrado o desactivado, y los nuevos reciben el snapshot actual; refresca `updated_at`; conserva `id`, `status`, `created_at`; sin `items` no toca las líneas; cuerpo vacío → 200 sin cambios; error de validación → 400 y el borrador queda como estaba (criterio 3).
- AC-08: al editar, el proveedor del borrador debe estar activo: si se desactivó y no se envía otro proveedor activo → 400 `supplier_id` (INV-01).
- AC-09: `GET /api/purchases/` lista paginada de la empresa, orden fecha desc, creación desc, id; `supplier_id` filtra (inválido → 400); cada fila trae `supplier.name`, `total`, `items_count`, `status`; aislamiento por empresa.
- AC-10: guardar (crear y editar) no crea ningún `StockMovement` ni `Expense` y no cambia saldos (INV-10).
- AC-11: sin token → 401; `purchases` deshabilitado para la empresa → 403 `module_disabled`; `PUT`/`DELETE` → 405.
- AC-12 (frontend, menú/rutas): Compras muestra «Compras» (`/pocketbiz/purchases`), «Proveedores», «Configuración» en es/en/de; `purchases`, `purchases/new`, `purchases/:id/edit` y `purchases/:id` cargan sus pantallas con `moduleGuard`; `purchases/suppliers` y `purchases/settings` siguen funcionando (declaradas antes de `:id`).
- AC-13 (lista): tabla Fecha, Proveedor, Referencia, Total, Estado, Acciones (ver, editar); paginación en servidor; «+ Nueva compra»; con `?supplierId` muestra el filtro con «Quitar filtro»; estados cargando, vacío (con y sin filtro) y error con «Reintentar».
- AC-14 (formulario, cabecera): proveedor activo obligatorio (búsqueda por nombre), fecha obligatoria (hoy por defecto), referencia y notas opcionales; sin proveedores se muestra «No hay proveedores activos.» y «Crear proveedor»; el diálogo «Nuevo proveedor» crea y selecciona el proveedor **sin perder lo escrito en el formulario**.
- AC-15 (formulario, líneas): agregar/quitar líneas; selector de producto activo con búsqueda por nombre y sin repetir ya elegidos; unidad base visible o «—»; cantidad > 0 y precio ≥ 0 validados con el error **junto a su línea**; subtotal por línea y total general de solo lectura calculados con la misma regla que el servidor (INV-06); etiqueta de moneda BOB; no hay campos de impuestos, descuentos ni costos adicionales; el total no es editable.
- AC-16 (formulario, guardado): «Guardar borrador» deshabilitado si es inválido o mientras guarda; en éxito, toast y navegación al detalle; ante error del servidor se conservan todas las entradas y los errores se muestran por campo y por línea; «Cancelar» vuelve a la lista (alta) o al detalle (edición) con aviso si hay cambios sin guardar.
- AC-17 (detalle): muestra proveedor (aunque inactivo), fecha, referencia («Sin referencia»), notas («Sin notas»), estado «Borrador», moneda BOB, líneas con subtotal y total; «Editar» solo si `editable`; no hay botón «Confirmar»; inexistente → aviso y retorno a la lista.
- AC-18 (edición): `/purchases/:id/edit` precarga cabecera y líneas del borrador y guarda con `PATCH`; si la compra no es editable redirige al detalle con aviso.

## Edge cases / Error cases
- EDGE-01: redondeo de subtotal: `0.333 × 10.00 = 3.33`; `1.005 × 1.00 = 1.01` (mitad hacia arriba); `0.001 × 0.01 = 0.00`.
- EDGE-02: importe que excede el máximo (total o subtotal) → error en la línea que lo provoca.
- EDGE-03: producto sin unidad base: cantidad con hasta 3 decimales; `unit_abbreviation=""` y la UI muestra «—».
- EDGE-04: producto de la compra renombrado o desactivado en el catálogo después de guardada: el detalle conserva el nombre acordado y la edición de otros campos no falla.
- EDGE-05: proveedor desactivado después de guardado el borrador: el detalle lo muestra; guardar sin cambiar de proveedor falla con error en `supplier_id` (AC-08).
- EDGE-06: `supplier_id`/`product_id` no UUID → error de campo (no 500).
- EDGE-07: lista vacía con y sin filtro; 404 al editar una compra ajena; error de red al guardar (conserva lo escrito).
- EDGE-08: enviar `items` con un producto repetido en distintas líneas marca la segunda línea.

## Authorization / permissions
Mismo modelo que Proveedores: usuario autenticado con empresa y módulo `purchases` habilitado (`CompanyModulePermission`, `required_modules = ('purchases',)`). Hoy solo existe el rol administrador. La empresa sale del usuario, nunca del cuerpo.

## API contract
API-01 … API-05 según el ADR `contrato-api-e-integracion-catalogo`: `GET/POST /api/purchases/`, `GET/PATCH /api/purchases/{id}/`, filtro `supplier_id`, forma de errores por línea, campos ignorados. Nuevo y aditivo; ningún contrato existente cambia. Catálogo suma `get_products_for_purchase` a su fachada.

## UI behavior
UI-01 menú «Compras»; UI-02 lista (plantilla Lista); UI-03 formulario con líneas (plantilla «Formulario con líneas», un paso); UI-04 detalle (plantilla Detalle); UI-05 diálogo «Nuevo proveedor». Detalle en el DDR.

## Non-functional requirements
Guardado atómico (cabecera + líneas en una transacción); listado sin N+1 (nombres de proveedor y conteo de líneas en consultas fijas); aislamiento por empresa en cada consulta; sin dependencias nuevas.

## Out of scope
Confirmar, cancelar o eliminar compras; recepción de mercadería y movimientos de inventario; creación de gastos; pagos a proveedores; impuestos, descuentos, costos adicionales; precios sugeridos desde el catálogo; numeración; filtros de lista distintos de proveedor; exportación; control optimista de concurrencia; estados distintos de `draft`.

## Open questions
Ninguna bloquea; los supuestos H-01…H-09 del TASK quedan como decisiones de este plan y pueden revertirse con aprobación: producto único por compra, cantidad decimal, borrador vacío permitido, snapshot conservado, proveedor activo en cada guardado, lista/detalle mínimos y diálogo de creación rápida de proveedor.

# Test Specification

## Unit tests
- `purchases/tests/test_purchase_domain.py` (sin BD): INV-01…INV-09, EDGE-01…03 y 08; cálculo con `Decimal`; snapshot conservado vs. nuevo; `replace_items` atómico (si falla una línea no cambia nada); el estado no se asigna.
- `purchases/tests/test_purchase_application.py` (repositorio y catálogo falsos): AC-03, AC-07, AC-08 con errores juntos de cabecera y líneas, producto inactivo solo rechazado si es nuevo, fraccionario vs. entero.
- Frontend (Karma): `purchase-amounts.spec.ts` (subtotal/total con los casos EDGE-01/02), `purchases-api.service.spec.ts` (mapeo de DTO y de errores por línea), `purchase-form.component.spec.ts`, `purchase-list.component.spec.ts`, `purchase-detail.component.spec.ts`, `supplier-quick-create` spec, `sidebar-menu.spec.ts` actualizado, prueba de orden de rutas.

## Integration tests
- `purchases/tests/test_purchase_api.py` (BD): AC-01…AC-11 con `APIClient`, incluidos aislamiento entre dos empresas, módulo deshabilitado, 405, no creación de `StockMovement`/`Expense` (AC-10), `float` y campos ignorados, y rollback ante error.
- `purchases/tests/test_purchase_repository.py` (BD): ida y vuelta del agregado, reemplazo de líneas, orden de lista, filtro por proveedor, `company_id`.
- `catalog/tests/test_services.py` (BD): `get_products_for_purchase` (propios, ajenos, inactivos, con y sin unidad).
- `purchases/tests/test_adapters.py` (BD): el adaptador `ProductCatalog` sobre la fachada real.
- Guardas existentes: `test_boundaries.py` (con `purchases → catalog` y `CONSUMERS`), `accounts/test_guards.py` (`company_id` en las tablas nuevas y `required_modules` en las rutas nuevas), `modularity/tests/test_enforcement.py` (rutas de compras bloqueadas sin el módulo).

## E2E
**NO.** El flujo se cubre con pruebas de API y de componente; no hay un flujo crítico de punta a punta que justifique Playwright (no instalado). La revisión visual manual se deja a `delivery-publish`.

## Regression tests
Suite completa de backend (`manage.py test`), `ng lint`, `ng build` y Karma de `features/purchases`, `sidebar-menu` y la prueba de rutas. Proveedores (`/purchases/suppliers`, `/purchases/settings`) debe seguir funcionando tras el reordenamiento de rutas.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01, AC-02 | `test_purchase_api` (crear), `test_purchase_domain` (derivados), `test_purchase_repository` |
| AC-03 | `test_purchase_domain`, `test_purchase_application`, `test_purchase_api` (400 con `items` por línea) |
| AC-04 | `test_purchase_domain` (tipos), `test_purchase_api` (float/NaN/exponente) |
| AC-05 | `test_purchase_api` (campos ignorados) |
| AC-06 | `test_purchase_api` (detalle, 404, otra empresa) |
| AC-07 | `test_purchase_application`, `test_purchase_api` (PATCH, snapshot conservado, rollback) |
| AC-08 | `test_purchase_application`, `test_purchase_api` |
| AC-09 | `test_purchase_api`, `test_purchase_repository` |
| AC-10 | `test_purchase_api` (conteo de `StockMovement`/`Expense`), `test_boundaries` (sin imports de inventory/expenses) |
| AC-11 | `test_purchase_api`, `test_enforcement`, `test_guards` |
| AC-12 | `sidebar-menu.spec.ts`, prueba de rutas, revisión de `routes.json` e i18n |
| AC-13 | `purchase-list.component.spec.ts` |
| AC-14 | `purchase-form.component.spec.ts` (selector, vacío, diálogo conserva el formulario), `supplier-quick-create` spec |
| AC-15 | `purchase-form.component.spec.ts`, `purchase-amounts.spec.ts` |
| AC-16 | `purchase-form.component.spec.ts` (guardar, error conserva entradas, cancelar) |
| AC-17 | `purchase-detail.component.spec.ts` |
| AC-18 | `purchase-form.component.spec.ts` (modo edición, no editable) |

# Implementation Plan

## Architecture considerations
Seguir `docs/architecture/ddd.md` y los dos ADR. Compras → Catálogo solo por puerto + adaptador en `infrastructure/adapters.py`. El proveedor se lee con el repositorio del mismo contexto. Los errores se mapean en la vista (patrón de `purchases/api/views.py::_run`).

## Proposed solution
Agregado `Purchase`/`PurchaseItem` puro; casos de uso `CreatePurchase`/`UpdatePurchase` (aplican las reglas que cruzan agregados y juntan errores); repositorio Django con transacción; API DRF con serializers de forma/tipos (cantidad y precio como strings → `Decimal` en el dominio); feature Angular con `PurchasesApiService`, función pura de importes y tres páginas + diálogo.

## Files/components affected
- **Backend nuevo** (`backend/modules/purchases/`): `domain/{purchase,enums}.py` y excepciones nuevas en `domain/exceptions.py`; `domain/repositories.py` (puerto `PurchaseRepository`); `application/{purchase_commands,purchase_queries,ports}.py`; `infrastructure/django/{models,mappers,purchase_repository}.py` (o extensión de los existentes) y `infrastructure/adapters.py`; `api/{purchase_serializers,purchase_views,purchase_urls}.py`; `migrations/0002_purchase.py`; tests listados arriba.
- **Backend modificado**: `catalog/services.py` (+ `ProductForPurchase`, `get_products_for_purchase`) y su test; `config/urls.py` (`api/purchases/`); `sales/tests/test_boundaries.py`; `modularity/tests/test_enforcement.py` (rutas de compras); `purchases/services.py` sin cambios de contrato.
- **Frontend nuevo** (`features/purchases/`): `models/purchase.ts`, `services/purchases-api.service.ts`, `services/purchase-amounts.ts`, `services/supplier-quick-create.service.ts`, `components/supplier-quick-create/*`, `pages/purchase-{list,form,detail}/*`, `testing/purchase-fixtures.ts` y specs; `purchases.routes.ts` (+ `PURCHASES_ROUTE`).
- **Frontend modificado**: `app.routes.ts` (la ruta `purchases` carga `PURCHASES_ROUTE`, declarada **después** de `purchases/suppliers` y `purchases/settings`), `assets/data/routes.json`, `assets/i18n/{es,en,de}.json`, `layout/sidebar/sidebar-menu.spec.ts`, `features/products/models/product.ts` (`BaseUnit.allowsFractions` opcional) y `services` de productos si hace falta mapearlo; `features/purchases/pages/supplier-detail` ya enlaza `/purchases?supplierId=` (se verifica).
- **Docs**: `docs/architecture/ddd.md` (nota de Compras), `docs/design/design-system.md` (variante de un paso en «Formulario con líneas»), `docs/producto/modulos-implementados.md`.

## Implementation steps
1. **Catálogo**: `ProductForPurchase` + `get_products_for_purchase` con pruebas (INV-04, INV-11).
2. **Dominio**: `Purchase`, `PurchaseItem`, `PurchaseStatus`, validaciones y cálculo; pruebas unitarias (INV-01…09, EDGE-01…03, 08).
3. **Aplicación**: puertos, `CreatePurchase`/`UpdatePurchase`/`GetPurchase`/`ListPurchases` con errores juntos (AC-03, AC-07, AC-08).
4. **Infraestructura**: modelos, migración `0002_purchase` (`makemigrations`), repositorio, mapper y adaptador (INV-10/11, AC-09).
5. **API**: serializers, vistas con `required_modules`, URLs y `config/urls.py` (AC-01…AC-11); actualizar `test_boundaries`, `test_guards`, `test_enforcement`.
6. **Frontend base**: modelo, servicio API, `purchase-amounts` con pruebas (AC-15).
7. **Páginas**: lista, formulario con líneas y diálogo de proveedor, detalle (AC-13…AC-18) siguiendo el DDR.
8. **Rutas, menú e i18n**: reordenar `app.routes.ts`, `routes.json`, es/en/de y `sidebar-menu.spec.ts` (AC-12).
9. **Documentación** y verificación local: `manage.py test`, `makemigrations --check`, `ng lint`, `ng build`, Karma del feature.

## Database / migrations
Migración nueva `purchases/migrations/0002_purchase.py` generada con `makemigrations` (tablas `purchases_purchase` y `purchases_purchase_item`, sin datos previos); no se edita `0001_initial`. Rollback: `migrate purchases 0001`.

## Risks
- Redondeo cliente/servidor (mitigado con función pura y pruebas de los mismos casos).
- Reordenar rutas (probado).
- Sin control de concurrencia (declarado fuera de alcance).
- `BaseUnit.allowsFractions` debe llegar al formulario desde la API de productos; si el servicio de productos no lo mapea, se añade el campo opcional.

## New dependencies
Ninguna.
