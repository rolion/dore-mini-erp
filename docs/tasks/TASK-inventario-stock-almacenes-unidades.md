# TASK-inventario-stock-almacenes-unidades: Productos que controlan stock, almacenes y unidades de medida (PB-INV-001 y PB-INV-002)

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-inventario-stock-almacenes-unidades
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/20

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-27 | (nuevo) → INVESTIGATION | Task creado; `main` al día. Las dos historias se entregan juntas (misma rama y PR) porque comparten el modelo de unidades | delivery-start |
| 2026-10-27 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | NEEDS_ARCHITECTURE (nuevo bounded context `inventory`, migraciones sobre productos existentes, nuevo puerto compartido) | delivery-start |
| 2026-10-27 | PLANNING → ENGINEERING | Specification READY tras 3 respuestas del usuario (ver Plan) | delivery-start |
| 2026-10-27 | ENGINEERING → REVIEW | Implementación completa según plan v1 | delivery-build |
| 2026-10-27 | REVIEW → ENGINEERING | Quality Gate FAIL (REV-01 High: specs del sidebar) | delivery-publish |
| 2026-10-27 | ENGINEERING → REVIEW | REV-01, 02, 04, 05, 06 corregidos; Karma completo = línea base | delivery-build |

## Investigación

### Requerimiento
**PB-INV-001 · Definir productos que controlan stock** (Inventario, P1, dep. PB-CFG-001). El administrador indica qué productos controlan existencias. En Catálogo → Productos se amplía la sección «Inventario» del formulario con «Controlar stock» (booleano, inicialmente desactivado) y «Unidad base» (selector obligatorio al controlar stock). El listado muestra nombre, precio, activo/inactivo, controla stock y unidad base (los datos de inventario solo con Inventario habilitado; sin costo ni valor). Cambiar unidad o control de stock con movimientos previos se bloquea con un mensaje que remite a la regularización; no se recalcula el pasado. Los productos antiguos quedan sin control de stock. Un producto sin control de stock se vende y compra sin pedir existencias.

**PB-INV-002 · Configurar almacenes y unidades de medida** (Inventario, P1, dep. PB-CFG-001). Inventario → Configuración con pestañas «Almacenes» y «Unidades», cada una con listado y formulario. Almacenes: nombre obligatorio, descripción opcional, predeterminado; la empresa sale de la sesión. Unidades: nombre y abreviatura obligatorios, admite fracciones, activo; sin conversiones ni unidad alternativa. Acciones: crear, editar, activar/desactivar, definir almacén predeterminado; buscar por nombre y filtrar por estado (inicial: activos). No se desactiva un almacén con saldo ≠ 0 o recepción pendiente (se muestra el motivo). Las unidades usadas no se eliminan ni cambian su significado: se desactivan para nuevas asignaciones. La empresa dispone de un almacén predeterminado, puede crear otros y no accede a almacenes ajenos.

**Aclaraciones del usuario (2026-10-27):**
1. Las empresas arrancan **sin unidades**; las crean en Inventario → Configuración → Unidades.
2. Los bloqueos que dependen de movimientos, saldos y recepciones se implementan como **puertos listos**; hoy esos datos no existen y responden «sin historial» (se prueban con dobles). No se crean tablas de movimientos ni recepciones.
3. Una unidad asignada a algún producto solo admite **activar/desactivar**: nombre, abreviatura y «admite fracciones» quedan bloqueados.

### Hechos encontrados
- `backend/modules/catalog/domain/product.py:46-88` — `Product` (id, name, description, sale_price, active, timestamps); métodos `rename/describe/change_price/activate/deactivate`. No existe stock ni unidad.
- `backend/modules/catalog/infrastructure/django/models.py:6-19` — `ProductModel` con `company_id` UUID sin FK; migraciones `0001_initial`, `0002_company_id`.
- `backend/modules/catalog/application/commands.py:12-55` — `CreateProduct`/`UpdateProduct` (sentinela `UNSET`, edición parcial, errores por campo).
- `backend/modules/catalog/api/views.py:46-88` y `serializers.py:6-21` — vistas finas con `required_modules = ('catalog',)`, `ProductInputSerializer` solo valida forma; `ProductSerializer` de solo lectura.
- `backend/modules/catalog/services.py:1-33` — fachada `get_product_for_sale` con DTO inmutable; Ventas no lee stock.
- `backend/modules/modularity/domain/modules.py:23-25` — módulo `inventory` ya existe en el catálogo (`requires=('catalog',)`, `optional=('sales','purchases')`); `backend/modules/` no tiene `inventory/`; `config/settings/base.py:20-26` no lo registra; `config/urls.py:13-24` no tiene rutas de inventario.
- `backend/shared/module_gate.py:1-39` — puerto neutro `register/enabled_keys/is_enabled` que implementa `modularity`; precedente para un puerto compartido sin que los módulos se importen.
- `backend/modules/sales/tests/test_boundaries.py:11-20` — `ALLOWED_DEPENDENCIES` exige una entrada por módulo de negocio (`test_every_business_module_has_a_declared_dependency_entry`); `inventory` hoy haría fallar ese test.
- `docs/architecture/ddd.md:1308-1325` — Inventory como evolución futura: `StockItem`, `StockMovement`, `Warehouse`, `InventoryAdjustment`; `ddd.md:844` mapa de dependencias de módulos.
- `frontend/panel_admin/src/app/features/products/` — `product-form` (Reactive Forms, `serverErrors` por campo), `product-list` (ngx-datatable con columnas Nombre/Precio/Estado/Acciones), `product-detail`, `models/product.ts` (DTO snake_case ↔ modelo camelCase), `services/products-api.service.ts`.
- `frontend/panel_admin/src/app/app.routes.ts:74-110` — `inventory` (placeholder `ComingSoonComponent`) e `inventory/settings` (`ModuleSettingsComponent` genérico: General vacío + Historial) con `moduleGuard`; `assets/data/routes.json:170-201` — submenú Inventario «Inicio» y «Configuración».
- `frontend/panel_admin/src/app/core/service/modules.service.ts:11-47` — `enabledKeys$`/`isDisabled(key)`: fuente para mostrar u ocultar la sección Inventario del formulario y las columnas.
- `docs/design/design-system.md:95-137` — plantillas Lista, Formulario, Detalle y Formulario de configuración con pestañas.

### Hipótesis / supuestos no confirmados
- PB-CFG-001 (dependencia) está publicada en `main` (PR #19); no bloquea.
- No hay roles distintos de `admin` hoy; «solo el administrador» equivale a `CompanyAdminPermission` por defecto.
- Las ventas/compras futuras consultarán `tracks_stock` por la fachada de Catálogo; esa integración queda fuera de este task.

### Módulos y dependencias relacionadas
`catalog` (producto y unidades), `inventory` (almacenes, nuevo), `modularity` (habilitación del módulo, solo vía `shared.module_gate`), `shared`, frontend `features/products`, `features/inventory` (nuevo), `layout/sidebar`, `app.routes.ts`.

### Implementaciones similares existentes
Backend: `expenses` (categorías con activar/desactivar y listado paginado) para el CRUD de unidades y almacenes; `modularity` para la siembra perezosa por empresa. Frontend: `features/expenses` (lista + diálogo de categoría) para listados con formulario en diálogo.

### Comportamiento actual
Los productos no tienen concepto de existencias; no hay unidades ni almacenes; «Inventario» es un placeholder más una pantalla de ajustes sin opciones.

### Restricciones
`CLAUDE.md`: aislamiento por `company_id` desde el usuario autenticado, módulos de negocio no se importan entre sí (solo `services`), dominio sin Django, nunca editar migraciones aplicadas, cantidades/dinero sin `float`, sin dependencias nuevas, sin abstracciones DDD innecesarias, fuera del MVP inventario avanzado (este task solo define las bases).

### Riesgos identificados
- Migración sobre `catalog_product` existente: `tracks_stock` con `default=False` mantiene el comportamiento de los productos antiguos (AC-02).
- Dependencia circular catalog⇄inventory si las unidades vivieran en Inventario (ver ADR).
- Los bloqueos por historial/saldo/recepciones no se ejercitan con datos reales hasta que existan movimientos; riesgo de olvidar enchufar los proveedores reales (se documenta y se prueba el contrato con dobles).
- Siembra concurrente del almacén predeterminado (dos primeras lecturas simultáneas).
- Suite frontend con fallos preexistentes (71 specs demo y `app.component.spec.ts`): comparar contra la línea base.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — nuevo bounded context `inventory`, cambio de modelo y migración sobre productos existentes, contrato API nuevo y modificado, nuevo puerto compartido y ajuste del mapa de dependencias.

### Diseño requerido
**SI** — se amplía el formulario/lista/detalle de productos y hay una pantalla nueva con pestañas (Almacenes, Unidades) y estados de bloqueo.

## Diseño
`docs/design/DDR-inventario-stock-almacenes-unidades-pantallas-inventario.md`

## Arquitectura
`docs/adr/ADR-inventario-stock-almacenes-unidades-propiedad-y-fronteras.md`

## Plan
`docs/plans/PLAN-2026-10-27-inventario-stock-almacenes-unidades.md` (v1, COMPLETO) · Specification readiness: READY

## Implementación
**Backend.** `shared/stock_history.py` (puerto neutro, INV-02). `catalog`: `domain/unit.py` (`UnitOfMeasure`, INV-03/04), `Product.tracks_stock/base_unit_id/configure_stock` (INV-01), `StockControl` + `CreateProduct/UpdateProduct` (INV-02, 08; AC-01, 03, 04), casos de uso de unidades, `DjangoUnitRepository` (nombre/abreviatura únicos sin distinguir mayúsculas, `in_use`), API `/api/units/` (API-02) con `required_modules=('inventory',)`, API de productos ampliada (API-01) con 409 `stock_history_locked`, migración `catalog/0003` (solo `CreateModel`/`AddField`, `tracks_stock` default False: AC-02). Nuevo `modules/inventory`: `Warehouse` (INV-06), casos de uso, puerto `WarehouseActivity` con adaptador nulo (INV-07), `DjangoWarehouseRepository` (siembra idempotente «Almacén principal», índice único parcial del predeterminado), API `/api/warehouses/` (API-03; AC-08, 09), migración `inventory/0001`, registro en settings/urls y `inventory: set()` en `test_boundaries.py`.
**Frontend.** `features/inventory/` (modelos, `UnitsApiService`, `WarehousesApiService`, diálogos, pestañas y `InventoryConfigurationComponent`; UI-03, UI-04), ruta `inventory/configuration` con `moduleGuard`, submenú e i18n es/en/de (UI-05). `features/products/`: modelo, servicio, formulario (sección «Inventario»: interruptor + selector, aviso de bloqueo), lista y detalle con datos de inventario solo con el módulo habilitado (UI-01, UI-02; AC-05).
**Pantallas de referencia:** `product-form`, `product-list`, `product-detail` y `category-list`/`category-dialog` (diálogo), `module-settings` (pestañas). Componentes reutilizados: badges `badge-outline`, botones `btn-tbl-*`, `NgbModal`, `ToastrService`. Se creó el parcial `inventory/components/_inventory-table.scss` (tabla apilada en móvil, copia del de módulos) y se documentó en `design-system.md`.
**Desviaciones del plan:** (1) Las pestañas de unidades/almacenes piden `page_size=100` y no muestran paginación (pocas filas por empresa). (2) Sin acción «Definir predeterminado» en el diálogo para activar/desactivar: se ofrece también como botón de estrella en la tabla. (3) `UnitOfMeasure.in_use` se calcula con un `Exists` sobre productos, no se guarda.
**Verificación propia (no es el Quality Gate):** backend `python manage.py test` → 712 tests OK; `makemigrations --check` sin cambios. Frontend: `npm run lint` OK, `ng build` OK, Karma acotado (products + inventory) 74/74 OK (se apartó temporalmente `app.component.spec.ts`, roto en `main`, y se restauró sin modificar).
**Entorno:** se copió `backend/.env` del checkout principal al worktree (con autorización del usuario; sin leerlo ni versionarlo, está en `.gitignore`), se usó el `.venv` del checkout principal y se enlazó `node_modules` con una unión.
**Corrección tras el primer Quality Gate (FAIL):** REV-01 (spec de `sidebar-menu.spec.ts`), REV-04 (`warehouse_default_changed` 409 en la carrera de make-default), REV-06 (`alert-warning`) y REV-05 (desviaciones: menú «Ajustes» en es.json; archivos `catalog/api/errors.py` e `inventory/api/pagination.py` no listados en el plan; fixture de `order-items.component.spec.ts`). Karma completo: 71 fallos = línea base, 567 OK. Backend inventory/catalog/modularity OK (con fallos intermitentes por reloj, REV-03).
**Deuda técnica:** los bloqueos por historial, saldo y recepciones no se ejercitan con datos reales hasta las historias de movimientos/recepciones (proveedor de `shared.stock_history` sin registrar; `NoWarehouseActivity`); no hay pantalla de regularización; el menú dice «Almacenes y unidades» y no «Configuración» literal; suite frontend con 71 specs demo preexistentes rotos.


## Review
_Pendiente_

## Publicación
_Pendiente_
