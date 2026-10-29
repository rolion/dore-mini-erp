# TASK-compras-borrador-crear-editar: Crear y editar compras en borrador (PB-COM-002)

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-compras-borrador-crear-editar
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/28

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-29 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-10-29 | INVESTIGATION → DESIGN | Veredicto NEEDS_ARCHITECTURE; diseño requerido | delivery-start |
| 2026-10-29 | DESIGN → ARCHITECTURE | DDR escrito | delivery-start |
| 2026-10-29 | ARCHITECTURE → PLANNING | ADR escritos | delivery-start |
| 2026-10-29 | PLANNING → ENGINEERING | Specification READY; PLAN v1 y PR abiertos | delivery-start |
| 2026-10-29 | ENGINEERING → REVIEW | Implementación y pruebas escritas | delivery-build |

## Investigación

### Requerimiento
PB-COM-002 · Crear y editar compras en borrador (Módulo Compras, P1, dependencia PB-COM-001). Como administrador, registrar una compra con sus productos y precios para organizar lo que se necesita adquirir.

- Menú y vistas: Compras → Compras → «Nueva compra»; formulario de borrador y vista de edición del mismo borrador.
- Cabecera: proveedor activo obligatorio, fecha de compra obligatoria, referencia externa opcional y notas opcionales. Sin proveedores: mostrar acceso a crearlos y conservar el formulario al volver.
- Líneas: selector de producto activo, nombre, cantidad positiva, unidad base cuando esté definida, precio unitario no negativo y subtotal calculado. Total general de solo lectura y moneda BOB.
- Acciones: agregar/quitar líneas, Guardar borrador, Cancelar edición y, posteriormente, Confirmar desde su detalle. Búsqueda de productos por nombre.
- Interfaz: cantidad/precio inválidos marcados junto a su línea, entradas conservadas ante errores, no se crean movimientos ni gastos al guardar; impuestos, descuentos y costos adicionales no aparecen como campos funcionales.
- AC: (1) el borrador incluye proveedor, fecha, referencia externa opcional, notas e ítems con cantidad > 0 y precio ≥ 0; (2) subtotal y total se calculan desde los ítems, el total no se edita y el MVP no tiene impuestos ni descuentos de compra; (3) un borrador se puede editar, no mueve stock ni registra gasto automático y conserva el nombre y precio acordados al confirmarse.

### Hechos encontrados
- La dependencia PB-COM-001 está integrada en `main` (PR #25, `e7fa547`): existe `backend/modules/purchases/` con solo el agregado `Supplier` (`domain/supplier.py:75-120`), `api/` en `/api/suppliers/` (`config/urls.py:19`), repositorio `DjangoSupplierRepository(company_id)` (`infrastructure/django/repositories.py`) y fachada `services.py:21-36` (`get_supplier_for_purchase`, `list_active_suppliers`) que anticipa que «la regla de proveedor activo la aplica quien compra».
- No existe ninguna entidad de compra: ni modelo, ni API, ni pantalla. Compras → «Inicio» (`/pocketbiz/purchases`) es «Próximamente» (`frontend/panel_admin/src/app/app.routes.ts:80-88`) y el submenú es «Inicio», «Proveedores», «Configuración» (`assets/data/routes.json:139-176`). El DDR de proveedores prometió que «Ver compras» navega a `/purchases?supplierId=<id>` (`docs/design/DDR-gestionar-proveedores-pantallas-proveedores.md`).
- `purchases` es módulo habilitable, deshabilitado por defecto, y depende de `catalog` y `expenses` (`modularity/domain/modules.py:23`; `docs/architecture/ddd.md:844`). Toda vista de negocio declara `required_modules` (`purchases/api/views.py:23`); un test lo exige para toda ruta (`accounts/test_guards.py:66-78`).
- El agregado análogo es `sales/domain/order.py`: cabecera con validación conjunta (`_validate_details`, `:112`), `OrderItem` con snapshot de nombre y precio (`:131-142`), importes derivados como propiedades (`:214-225`), duplicados rechazados (`add_item`), `ensure_editable`. Su dinero usa `shared/domain/money.py:parse_money` (Decimal, 2 decimales, 0…9 999 999 999.99). La moneda es única e implícita (`money.py` docstring); el frontend muestra «Bs » con `MoneyPipe` (`shared/pipes/money.pipe.ts`). «BOB» no aparece hoy en el código.
- Cantidades: Ventas usa enteros (`order.py:validate_quantity`); Inventario usa `Decimal` con 3 decimales (`inventory/domain/adjustment.py:12-14`) y el catálogo define por unidad `allows_fractions` (`catalog/domain/unit.py`, `catalog/domain/product.py:UnitSummary`). `Product.base_unit` es opcional y solo se exige con `tracks_stock` (`product.py:configure_stock`).
- Catálogo expone hacia otros módulos solo `ProductForSale` y `ProductForInventory` (`catalog/services.py:15-66`); este último ya trae `name, active, unit_abbreviation, allows_fractions` pero está nombrado para inventario. Ventas lo consume desde `sales/infrastructure/adapters.py` (puertos en `sales/application/ports.py`).
- Límites verificados por AST: `ALLOWED_DEPENDENCIES['purchases'] = set()` y `CONSUMERS = ('sales','reporting','inventory')` (`sales/tests/test_boundaries.py:12-24`); hay que declarar `purchases → catalog` y añadir `purchases` a `CONSUMERS` (solo desde `adapters.py`).
- Frontend de referencia: `features/purchases/` (lista/forma/detalle de proveedores, `suppliers-api.service.ts`, `purchases.routes.ts` con `SUPPLIERS_ROUTE`); `features/sales/pages/order-form` (ng-select con typeahead y pie «+ Nuevo cliente» vía `CustomerQuickCreateService`, `unsavedChangesGuard`), `features/sales/components/order-items` (selector de producto activo con `ProductsApiService`), y la plantilla «Formulario con líneas» del sistema de diseño (`docs/design/design-system.md:141-143`, `features/inventory/pages/stock-opening`). `Product.baseUnit` del frontend no trae `allowsFractions` aunque la API sí lo devuelve (`catalog/api/serializers.py:19-24`, `features/products/models/product.ts:1-6`).
- Orden de rutas de `app.routes.ts`: `purchases/suppliers` y `purchases/settings` son hermanas declaradas después de `purchases` (`:99-111`); si `purchases` pasa a tener hijos con `:id`, tienen que declararse antes o `suppliers` se interpretaría como un id.
- Estado de datos: `ModulesService.isDisabled('customers')` (patrón de integraciones opcionales) no aplica: Catálogo es base y siempre está activo.

### Hipótesis / supuestos no confirmados
Decididos aquí por criterio y registrados en el PLAN (§Open questions); ninguno cambia el contrato de forma irreversible:
- H-01 **Cantidad decimal** (hasta 3 decimales, como Inventario) y **entera** cuando la unidad base del producto no admite fracciones; sin unidad base definida se admiten hasta 3 decimales.
- H-02 **Un producto aparece una sola vez por compra** (como en Ventas); para comprar el mismo producto a dos precios se usan dos compras o se promedia.
- H-03 Subtotal de línea = cantidad × precio unitario redondeado a 2 decimales (mitad hacia arriba); total = suma de subtotales. Máximo 200 líneas por compra.
- H-04 Un borrador puede guardarse **sin líneas** (borrador de trabajo); exigir ≥ 1 línea es regla de Confirmar (otra task).
- H-05 El nombre del producto (y su unidad) se copia al agregar la línea y **se conserva** en ediciones posteriores del borrador mientras el producto siga en él; renombrarlo en el catálogo no cambia el borrador. Los productos ya incluidos no se revalidan como activos al editar; los nuevos sí.
- H-06 Todo guardado exige un **proveedor activo** (también al editar un borrador cuyo proveedor se desactivó: hay que cambiarlo).
- H-07 Alcance de pantallas: se entrega lo mínimo para llegar al formulario y verlo — lista de compras (solo lectura, con filtro por proveedor para «Ver compras») y detalle de solo lectura con «Editar» — sin Confirmar, Cancelar compra, filtros avanzados ni exportación (tasks posteriores).
- H-08 Sin proveedores: el selector ofrece «+ Nuevo proveedor» en un **diálogo de creación rápida** (patrón de Clientes); como no se sale de la pantalla, el formulario se conserva por construcción.
- H-09 La moneda BOB es fija e informativa (`currency: "BOB"` en la API, etiqueta en pantalla); no hay campo ni conversión.

### Módulos y dependencias relacionadas
`purchases` (propietario), `catalog` (nueva lectura vía fachada), `modularity` (compuerta; sin cambios), `inventory` y `expenses` (**no** se tocan: guardar un borrador no genera movimientos ni gastos).

### Implementaciones similares existentes
`sales` (agregado con líneas y snapshots), `customers` (CRUD y creación rápida), `inventory/pages/stock-opening` (formulario con líneas).

### Comportamiento actual
`/api/purchases/` no existe (404). Compras → «Inicio» muestra «Próximamente». No hay forma de registrar una compra.

### Restricciones
`CLAUDE.md`: dinero en `Decimal`, aislamiento por `company_id` desde el usuario autenticado, dominio sin Django, módulos solo por fachadas, estados por métodos del agregado, migración nueva (no editar aplicadas), sin dependencias nuevas, Reactive Forms y sin `any` en Angular.

### Riesgos identificados
- Redondeo: el navegador muestra subtotales/total mientras se edita; si difiere del servidor, confunde. Mitigación: función pura con aritmética entera (BigInt) que replica la regla, probada con casos límite, y el servidor es la fuente de verdad tras guardar.
- Reordenar rutas de `app.routes.ts` puede romper `purchases/suppliers` y `purchases/settings`; se cubre con pruebas de rutas.
- Dos usuarios editando el mismo borrador a la vez (último en guardar gana). Mitigación: guardado atómico con bloqueo de fila; control optimista fuera de alcance.
- Reemplazo de líneas en cada guardado: las líneas cambian de id entre guardados. Aceptable mientras nada las referencie; Confirmar (task posterior) las congela.
- Nueva dependencia `purchases → catalog` y primer adaptador de Compras: hay que actualizar los tests de límites.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — nuevo agregado con líneas, tabla y migración, nuevo contrato API, nueva dependencia entre módulos (`purchases → catalog`) y reglas de dinero/cantidad.

### Diseño requerido
**SI** — formulario con líneas, lista y detalle nuevos, entrada de menú y diálogo de creación rápida de proveedor.

## Diseño
Ver `docs/design/DDR-compras-borrador-crear-editar-pantallas-compras.md`.

## Arquitectura
- `docs/adr/ADR-compras-borrador-crear-editar-modelo-compra-borrador.md`
- `docs/adr/ADR-compras-borrador-crear-editar-contrato-api-e-integracion-catalogo.md`

## Plan
`docs/plans/PLAN-2026-10-29-compras-borrador-crear-editar.md` (v1, COMPLETO).

## Implementación

**Resumen.** Agregado `Purchase`/`PurchaseItem` en `backend/modules/purchases/`, API `/api/purchases/`, lectura de Catálogo por puerto + adaptador y feature Angular de lista, formulario con líneas, detalle y diálogo de creación rápida de proveedor, con el menú «Compras» y las rutas reordenadas.

| Parte | Cubre |
|---|---|
| `domain/purchase.py`, `domain/enums.py`, `domain/exceptions.py`, `domain/repositories.py` | INV-01…09, INV-12, AC-01…05, EDGE-01…03, 08 |
| `application/{purchase_commands,purchase_queries,ports}.py` | INV-01, INV-04 (producto activo solo si es nuevo), INV-08, AC-03, AC-07, AC-08 |
| `infrastructure/django/{models,mappers,purchase_repository}.py`, `migrations/0002_purchase.py`, `infrastructure/adapters.py` | INV-10, INV-11, AC-09 |
| `api/purchase_{serializers,views,urls}.py`, `config/urls.py` | AC-01…AC-11 (`required_modules = ('purchases',)`) |
| `catalog/services.py` (`ProductForPurchase`, `get_products_for_purchase`) | INV-04, INV-11 |
| `features/purchases/{models,services,pages,components}` | AC-13…AC-18, UI-02…UI-05 |
| `app.routes.ts`, `routes.json`, `i18n/{es,en,de}.json` | AC-12, UI-01 |
| `features/products` (`BaseUnit.allowsFractions`) | AC-15 (cantidad entera según unidad) |

**Pruebas escritas:** backend `purchases/tests/{test_purchase_domain,test_purchase_application,test_purchase_api,test_purchase_repository}.py` y `GetProductsForPurchaseTests` en `catalog/tests/test_services.py`; guardas actualizadas (`sales/tests/test_boundaries.py`, `accounts/test_guards.py` con `PurchaseItemModel` como tabla hija, `modularity/tests/test_enforcement.py` con las rutas nuevas). Frontend: specs de importes, servicio, formulario, lista, detalle, diálogo y orden de rutas; `sidebar-menu.spec.ts` actualizado.

**Verificación propia (no es el Quality Gate):**
- Backend: `test_purchase_domain` + `test_purchase_application` + `test_boundaries` + `test_guards` sin BD → OK. Los tests con BD (`test_purchase_api`, `test_purchase_repository`, `catalog.test_services`, `test_enforcement`) se ejecutaron **solo contra una base SQLite desechable** (`purchases` + `catalog.test_services` + `test_enforcement` + `test_boundaries` + `test_guards`: 149 tests OK) porque este worktree no tiene `DATABASE_URL`/credenciales de PostgreSQL y no se leyó el `.env`. **No se corrieron contra PostgreSQL ni la suite completa de `manage.py test`:** `delivery-publish` debe hacerlo (en SQLite `select_for_update` no bloquea).
- `makemigrations --check` sin cambios pendientes tras generar `0002_purchase`.
- Frontend: `ng lint` OK; `ng build` OK; Karma (Chrome headless, con un tsconfig temporal ya eliminado que excluye `app.component.spec.ts` por su fallo de compilación preexistente) sobre `features/purchases`, `features/products` y `layout/sidebar`: 154/154. No se corrió el Karma completo.
- Se creó una *junction* local `frontend/panel_admin/node_modules` → checkout principal (ignorada por git, sin instalar dependencias) para poder compilar.

**Desviaciones respecto al plan:** ninguna de alcance. Detalles: (a) el índice por proveedor se llama `purch_purch_company_supplier` (el nombre del plan superaba los 30 caracteres de Django); (b) los archivos nuevos del backend usan el prefijo `purchase_` (`purchase_views.py`, `purchase_urls.py`, `purchase_repository.py`, `purchase_commands.py`, `purchase_queries.py`) junto a los de proveedores en vez de ampliarlos; (c) `quantity` y `unit_price` en texto aceptan solo decimales simples (sin exponente, `NaN` ni separadores) además de lo que ya excluía el plan; (d) el `4xx` por «demasiadas líneas» llega como `items: ["…"]` (lista de textos) y la interfaz lo muestra como aviso general.

**UI:** pantallas de referencia: Lista → `purchases/pages/supplier-list`; Formulario con líneas → `inventory/pages/stock-opening` y `sales/pages/order-form` (selector con pie «+ Nuevo …»); Detalle → `supplier-detail`. Reutiliza `MoneyPipe`, `Page<T>`, `table-actions`, `unsavedChangesGuard`, `ProductsApiService` y `SuppliersApiService`. Componente nuevo propio de la feature: `SupplierQuickCreateComponent` (+ servicio), no compartido. Sin HEX ni estilos sueltos.

**Deuda técnica:** validación de correo duplicada entre diálogo, formulario de proveedor y dominio (patrón de clientes); el selector de producto repite el de `order-items`; sin control optimista de concurrencia (declarado en el plan); `BaseUnit.allowsFractions` es opcional porque algunas fixtures no lo traen.

**Documentación actualizada:** `docs/architecture/ddd.md`, `docs/design/design-system.md` (variante de un paso), `docs/producto/modulos-implementados.md`.

## Review
_Pendiente_

## Publicación
_Pendiente_
