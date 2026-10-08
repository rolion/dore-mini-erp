# TASK-catalogo-productos-mvp: Catálogo de productos (crear, editar, activar/desactivar, listar, consultar) + menú

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** `task/TASK-catalogo-productos-mvp`
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/5

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-08 | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-10-08 | DESIGN → ARCHITECTURE | Decisión de diseño registrada en DDR (menú reducido; lista, formulario y detalle como páginas) | delivery-design |
| 2026-10-08 | ARCHITECTURE → PLANNING | Decisiones registradas en 3 ADR (módulo `catalog`, contrato API, feature frontend) | delivery-architect |
| 2026-10-08 | PLANNING → ENGINEERING | Plan v1 COMPLETO, Specification READY; PR #5 abierto | delivery-plan |
| 2026-10-08 | ENGINEERING → REVIEW | Implementación completa según plan v1 (backend `catalog`, frontend `features/products`, menú) | delivery-engineer |
| 2026-10-08 | REVIEW → PUBLISH | Review PASS (0 issues Critical/High; 1 Low abierto) | delivery-review |

## Investigación

### Requerimiento
Implementar el módulo **Catálogo** (REQ-CAT-001 a REQ-CAT-005, todos del bounded context Catalog):

- **REQ-CAT-001 Crear producto** (MVP-Alta): nombre obligatorio; precio de venta ≥ 0; se crea activo por defecto. Aceptación: datos válidos → queda disponible en el catálogo; sin nombre o precio inválido → se rechaza.
- **REQ-CAT-002 Editar producto** (MVP-Alta): editar nombre, descripción, precio; el catálogo refleja los nuevos valores; los pedidos anteriores conservan snapshot de nombre y precio; los cambios aplican solo a operaciones futuras.
- **REQ-CAT-003 Activar/desactivar** (MVP-Alta): producto inactivo no puede agregarse a nuevos pedidos y deja de ser seleccionable; las ventas/reportes históricos lo siguen mostrando.
- **REQ-CAT-004 Listar** (MVP-Alta): filtro por estado activo/inactivo y búsqueda por nombre.
- **REQ-CAT-005 Consultar** (MVP-Media): detalle con estado, precio y datos descriptivos; sin mezclar ventas históricas en la entidad Catalog.

Pedido adicional del usuario (frontend): en el menú lateral borrar las opciones actuales y conservar solo "Dashboard"; agregar menú "Catálogo" con submenú "Producto"; al hacer clic se muestra el listado de productos en una tabla de la plantilla; se debe poder agregar, editar y ver el detalle completo.

### Hechos encontrados

**Backend — estado actual**
- `backend/modules/` contiene solo `accounts` (`backend/modules/accounts/apps.py:4-6`); **no existe `catalog`** ni ninguno de los otros bounded contexts. `docs/architecture/ddd.md:105-226` define el módulo Catalog pero aún no está implementado.
- `backend/config/settings/base.py:11-21` — `INSTALLED_APPS` solo registra `rest_framework`, `rest_framework.authtoken` y `modules.accounts`.
- `backend/config/urls.py:6-10` — solo existen `admin/`, `api/health/` y `api/auth/` (login/logout, `backend/modules/accounts/api/urls.py:4-7`).
- `backend/config/settings/base.py:70-85` — DRF configurado con `TokenAuthentication` + `SessionAuthentication`, permiso por defecto `IsAuthenticated`, solo `JSONRenderer`, y **paginación por defecto `PageNumberPagination` con `PAGE_SIZE: 50`**. No hay `django-filter` en `backend/requirements/base.txt` (solo Django, DRF, psycopg, django-environ).
- `backend/modules/accounts/api/views.py:32-59` — patrón de vistas existente: `APIView` con serializers en `api/serializers.py`; no hay ViewSets ni routers todavía.
- `backend/shared/__init__.py` existe pero está vacío (el DDD prevé `shared/domain/money.py`, `ids.py`, `exceptions.py` en `docs/architecture/ddd.md:811-826`).
- Base de datos PostgreSQL por `DATABASE_URL` (`backend/config/settings/local.py:8`, `test.py:8`, `production.py:8`). Única migración existente: `backend/modules/accounts/migrations/0001_initial.py`; Catalog tendría su propia `0001`.

**Reglas de dominio ya documentadas** (`docs/architecture/ddd.md`)
- `:123-134` atributos sugeridos de Product: `id, name, description, sku, sale_price, active, created_at, updated_at`.
- `:149-174` Money(amount, currency) con `Decimal`; ProductId puede ser UUID.
- `:176-181` reglas: nombre obligatorio; precio no negativo; producto desactivado no se agrega a nuevos pedidos; se mantiene históricamente.
- `:187-205` Commands: CreateProduct, UpdateProduct, ActivateProduct, DeactivateProduct, ChangeProductPrice. Queries: GetProduct, ListProducts, SearchProducts, ListActiveProducts.
- `:210-224` ProductRepository con interfaz en dominio e implementación Django en infraestructura.
- `:920-928` endpoints sugeridos: `GET/POST /api/products`, `GET/PATCH /api/products/{id}`, `POST /api/products/{id}/deactivate` (no menciona `activate`).
- `:374-376` OrderItem guarda snapshot de `product_name` y `unit_price` (módulo Sales, inexistente hoy).
- `:910-912` el propio documento dice que no es obligatorio separar modelos Django y entidades en el MVP salvo dominios con lógica relevante (Sales).
- `CLAUDE.md` — dinero en `Decimal`; estados se cambian por métodos del agregado; el dominio no importa Django; avisar antes de instalar dependencias; frontend en `src/app/features/<modulo>/`.

**Frontend — menú lateral**
- `frontend/panel_admin/src/app/layout/sidebar/sidebar.service.ts:20-21` — el menú se carga con `GET assets/data/routes.json`; `sidebar.component.ts:94-99` solo lo carga si hay usuario autenticado.
- `frontend/panel_admin/src/assets/data/routes.json` — contiene 21 entradas (grupo "Principal", Home con Dashboard1/Dashboard2, Advance Table, Apps, Calendar, Email, etc.). El tipo es `RouteInfo` (`sidebar.metadata.ts:2-12`: `path, title, iconType, icon, class, groupTitle, badge, badgeClass, submenu`).
- `frontend/panel_admin/src/app/layout/sidebar/sidebar.component.html:25-88` — renderiza hasta 3 niveles; `title` pasa por el pipe `translate`; un ítem con `submenu` usa `class: "menu-toggle"` y `path: ""`; sin submenu `class: ""` con `path`.
- Las claves de título están en `frontend/panel_admin/src/assets/i18n/{en,es,de}.json` bajo `MENUITEMS` (línea 7 de cada uno). `app.config.ts:25-27` fija `defaultLanguage: 'en'` y `language.service.ts:19-23` elige el idioma del navegador entre en/es/de, con `en` como fallback.
- `sidebar.component.html:5` — el logo enlaza a `/dashboard/main`; `:20-21` muestra un nombre de usuario fijo "Emily Smith" y `MENUITEMS.USER.POST`.
- `frontend/panel_admin/src/app/dashboard/dashboard.routes.ts:6-18` — `dashboard` redirige a `main`; también existe `dashboard2`.

**Frontend — rutas y estructura**
- `frontend/panel_admin/src/app/app.routes.ts:7-105` — rutas hijas con `loadChildren` perezoso bajo `MainLayoutComponent` + `AuthGuard`; hay ~15 secciones de demo (advance-table, apps, calendar, email, ui, forms, charts, icons, maps, tables, data-tables, etc.) y un `**` → `Page404Component` (`:112`).
- **No existe** `frontend/panel_admin/src/app/features/` (verificado); `CLAUDE.md` y `ddd.md:980-1004,1035-1046` piden `features/<modulo>/{pages,components,services,models}` con `products-api.service.ts`.
- `frontend/panel_admin/src/app/core/interceptor/jwt.interceptor.ts:7-13` — añade `Authorization: Token <token>` a URLs que empiezan por `environment.apiUrl` (`'/api'`, `src/environments/environment.ts:3`). `proxy.conf.json` enruta `/api` → `http://127.0.0.1:8000`.
- `frontend/panel_admin/src/app/core/guard/auth.guard.ts:14-19` — el guard ya valida `isAuthenticated` (token real).

**Frontend — componentes de plantilla reutilizables para la tabla y formularios**
- Tabla con búsqueda, botón agregar y acciones editar/eliminar: `src/app/advance-table/advance-table.component.html:12-116` (`ngx-datatable class="material"`, buscador `table-search-area`, modales `NgbModal` para alta/edición, `Swal` para confirmaciones — `advance-table.component.ts:4,6,65,98`). Está alimentada por JSON local (`datatable-data.json`) y filtra/pagina en el cliente.
- Tabla simple de `ngx-datatable`: `src/app/data-tables/basic-datatable/basic-datatable.component.html:1-60`; badges de estado `badge-outline col-green|col-red` (`:51-60` y `advance-table.component.html:83-98`).
- Formulario con validación y mensajes `text-danger`: `src/app/forms/form-validation/form-validation.component.html:1-50` (estructura `main-content` → `breadcrumb-style` → `section-body` → `card`).
- Dependencias ya instaladas: `@swimlane/ngx-datatable ^22`, `@ng-bootstrap/ng-bootstrap 20`, `ngx-toastr ^19`, `sweetalert2` (`frontend/panel_admin/package.json:31,39,62,65`).

**Dominio de ventas**
- No existe módulo Sales/Order en backend (solo `accounts`). Por tanto no hay hoy pedidos ni "snapshots" que verificar ni "nuevos pedidos" donde bloquear productos inactivos.

### Hipótesis / supuestos no confirmados
- Se asume que los textos de UI van en español (CLAUDE.md y mensajes de login lo están), pero la plantilla se carga en `en` por defecto si el navegador no es es/de; no se confirmó qué idioma debe mostrarse el menú "Catálogo / Producto".
- "Borrar las opciones que tenemos ahora" se interpreta como quitar todas las entradas de `routes.json` salvo Dashboard; no se confirmó si se conservan las **rutas** de demo (`app.routes.ts`) o solo el menú, ni si se mantiene Dashboard 2 como subítem o solo `/dashboard/main`.
- "Ver el detalle completo" se interpreta como una pantalla/vista de detalle de solo lectura (REQ-CAT-005); no se confirmó si debe ser página aparte, modal o fila expandible.
- La activación/desactivación (REQ-CAT-003) probablemente deba estar en la UI (botón/interruptor en la lista o el detalle) aunque el pedido textual del usuario solo menciona agregar, editar y ver detalle; no confirmado.
- No se confirmó si el campo `sku` y la moneda (`Money.currency`, ejemplo "BOB") son parte del MVP; los REQ-CAT solo nombran nombre, descripción, precio y estado.
- No se confirmó si el `name` debe ser único ni longitudes máximas; los REQ no lo definen.
- Volumen de datos esperado y si la lista debe paginar/buscar en servidor (hoy `PAGE_SIZE=50`) no está definido.
- No se verificó si hay datos de productos en la base ni migraciones pendientes (no se leyó `.env` ni se consultó la base).

### Módulos y dependencias relacionadas
- **Backend:** nuevo bounded context `catalog` (capas `domain`/`application`/`infrastructure`/`api` según `ddd.md:49-80`, creadas solo si hacen falta), registro en `INSTALLED_APPS` y `config/urls.py`, nueva migración inicial de la app. Dependencia futura (no implementada): `sales` consume Catalog por id/servicio de aplicación, nunca por modelos (`ddd.md:772-807`); `reporting` solo lee.
- **Frontend:** `layout/sidebar` (+ `assets/data/routes.json` y `i18n/*.json`), `app.routes.ts`, nueva carpeta `features/products/` (por `ddd.md:1035-1046`), consumo de la API con el interceptor de token existente. Reutiliza `ngx-datatable`, `NgbModal`/páginas, `ngx-toastr` y `sweetalert2` de la plantilla.
- **Cruza límites de módulo:** no (Sales/Reporting no existen aún).

### Implementaciones similares existentes
- Vistas/serializers: único precedente backend es `accounts` (`APIView` + serializers, `api/urls.py`); no hay CRUD ni ViewSet que seguir, ni tests de API de recurso.
- Frontend: `advance-table` es el patrón de tabla + búsqueda + alta/edición por modal de la plantilla (con datos locales, sin servicio HTTP); `core/service/auth.service.ts:29-48` es el único servicio que habla con la API real (patrón `HttpClient` + `environment.apiUrl`).
- Las pantallas de la plantilla usan `UntypedFormBuilder` (p. ej. signin) y modelos sin tipos explícitos; `CLAUDE.md` exige Reactive Forms tipados y sin `any`, por lo que no se pueden copiar tal cual.

### Comportamiento actual
- Al autenticarse, el usuario ve un menú lateral de 21 entradas con las páginas de demo de la plantilla; no existe ninguna pantalla ni endpoint de productos. `GET /api/products` hoy devolvería 404 (la URL no existe en `config/urls.py:6-10`).
- Las pantallas de tabla de la plantilla cargan datos JSON estáticos locales, no una API.

### Restricciones
- `CLAUDE.md`: acotar cambios a un objetivo y **proponer plan y esperar confirmación antes de tocar varios archivos**; dinero en `Decimal`; nunca editar migraciones aplicadas; no tocar `.env`; **avisar antes de instalar dependencias** (filtrado por estado/búsqueda podría resolverse sin `django-filter`, pero no se evaluó aquí); dominio sin imports de Django; estados vía métodos del agregado; serializers validan forma y tipos; no añadir abstracciones DDD sin necesidad real; frontend con Reactive Forms, tipos explícitos, sin `any` y sin suscripciones colgadas; una rama y un PR por task (`task/TASK-<slug>`).
- Fuera del MVP (`ddd.md:1205-1222`): inventario/producción avanzados, CQRS completo, event sourcing.
- `ddd.md:176-181` y los REQ imponen: nombre obligatorio, precio ≥ 0, activo por defecto.

### Riesgos identificados
- **Primer bounded context de negocio:** su forma (modelo Django vs entidad de dominio + repositorio + mapper; ubicación de `Money`/`shared`) sienta precedente para Customers/Sales/Expenses; el propio `ddd.md` deja la separación como opcional.
- **Reglas dependientes de módulos inexistentes:** snapshot en pedidos (REQ-CAT-002), bloqueo de inactivos en nuevos pedidos y visibilidad histórica (REQ-CAT-003) solo pueden quedar como invariantes/contrato del catálogo; no son verificables extremo a extremo hasta que exista Sales.
- **Contrato de API no definido:** paginación (hoy `PageNumberPagination` 50), filtros por estado y búsqueda por nombre, formato de `sale_price` en JSON (Decimal como string) y activación (`ddd.md:927` solo lista `deactivate`) deben quedar fijados porque lo consumirá el frontend.
- **Menú y rutas:** `routes.json` y las claves i18n están repartidas en 3 idiomas; quitar entradas sin quitar rutas deja páginas de demo accesibles por URL; las rutas demo siguen cargándose en `app.routes.ts`.
- **Plantilla vs reglas del proyecto:** los componentes de ejemplo usan formularios no tipados y datos locales; adaptarlos a servicio HTTP, paginación y tipos estrictos requiere criterio de diseño.
- **Sin tests de recurso en backend** (solo `modules/accounts/tests.py` y `config/tests.py`) ni specs de feature en frontend como referencia.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — Se crea el primer bounded context de negocio (`catalog`) con nuevo modelo de base de datos, migración inicial y API REST completa, y su estructura de capas/repositorio/Money fija el patrón del resto de módulos; además hay decisiones de contrato (paginación, filtros, activación) con impacto futuro en Sales y Reporting.

### Diseño requerido
**SI** — Se agregan pantallas nuevas (listado en tabla, alta/edición, detalle) con componentes de la plantilla y se rediseña el menú lateral (de 21 entradas a Dashboard + Catálogo/Producto); hay que decidir cómo se presentan alta/edición/detalle (modal vs página) y cómo se resuelve la activación para mantener la consistencia visual con el resto de la plantilla.

## Diseño
- [DDR-catalogo-productos-mvp-menu-y-pantallas-producto](../design/DDR-catalogo-productos-mvp-menu-y-pantallas-producto.md) — Propuesto. Menú: Dashboard + Catálogo ▸ Producto; lista con `ngx-datatable` (búsqueda, filtro de estado, activar/desactivar con confirmación); formulario de alta/edición y detalle como páginas con URL propia.
- Pendiente para arquitectura: campos finales del producto (SKU/moneda), unicidad del nombre, paginación y filtros en servidor, endpoints de activar/desactivar.

## Arquitectura
- [ADR-catalogo-productos-mvp-modelo-dominio](../adr/ADR-catalogo-productos-mvp-modelo-dominio.md) — módulo `catalog` con entidad `Product` de dominio puro, casos de uso, repositorio/mapper Django, UUID; sin SKU, moneda, `Money` ni unicidad de nombre.
- [ADR-catalogo-productos-mvp-contrato-api](../adr/ADR-catalogo-productos-mvp-contrato-api.md) — `/api/products/`: lista con `search`/`active`/paginación en servidor, alta, detalle, PATCH, `activate`/`deactivate`; sin DELETE; errores 400 por campo.
- [ADR-catalogo-productos-mvp-frontend-feature](../adr/ADR-catalogo-productos-mvp-frontend-feature.md) — `features/products`, rutas `catalog/products*`, menú; las rutas de demo solo salen del menú.
- Sin dependencias nuevas; cambios aditivos con rollback por revert de PR / `migrate catalog zero`.

## Plan
- [PLAN-2026-10-08-catalogo-productos-mvp](../plans/PLAN-2026-10-08-catalogo-productos-mvp.md) — v1, Modo COMPLETO, Specification readiness: READY. 13 ACs (API, menú, lista, formulario, detalle), 5 invariantes, sin dependencias nuevas, E2E: NO (verificación manual de humo).

## Implementación
Rama `task/TASK-catalogo-productos-mvp`, PR #5, siguiendo el plan v1 (COMPLETO).

**Backend** (`backend/modules/catalog/`)
- `domain/` — `Product` (dataclass sin Django), `validate_name`/`validate_price`, `ProductValidationError`, `ProductNotFound`, `ProductRepository` (Protocol): INV-01..04, AC-02, AC-03.
- `application/` — `CreateProduct`, `UpdateProduct` (parcial, junta errores de varios campos, no guarda si no hay cambios), `ActivateProduct`, `DeactivateProduct`, `GetProduct`, `ListProducts`: AC-01, AC-04..AC-07.
- `infrastructure/django/` — `ProductModel` (UUID, `Decimal(12,2)`, orden `name,id`), mapper, `DjangoProductRepository` y `ProductList` (vista perezosa para paginar sin cargar todo); `migrations/0001_initial.py` generada con `makemigrations`.
- `api/` — serializers de entrada/salida, vistas `APIView` delgadas (`_run` traduce dominio→400/404), `ProductPagination` (`page_size` máx. 100), urls con `<uuid:product_id>`; montado en `config/urls.py` como `api/products/` y app registrada en `INSTALLED_APPS`: AC-01..AC-08, INV-05 (no hay `DELETE`/`PUT`).

**Frontend** (`frontend/panel_admin/src/app/features/products/`)
- `models/product.ts`, `services/products-api.service.ts` (DTO snake_case ↔ modelo camelCase, errores 400 por campo → `ProductApiError`).
- `pages/product-list` (ngx-datatable con paginación externa, buscador con debounce, filtro de estado, confirmación `Swal` + `toastr`), `pages/product-form` (alta/edición, `FormBuilder` tipado, errores del servidor bajo cada campo), `pages/product-detail`; `products.routes.ts` y ruta `catalog/products` en `app.routes.ts`: AC-10..AC-13.
- Menú: `assets/data/routes.json` reducido a Dashboard + Catálogo ▸ Producto y claves `MENUITEMS.*` en en/es/de: AC-09.
- `docs/architecture/ddd.md`: agregado `POST /api/products/{id}/activate`.

**Tests escritos**
- Backend: `test_domain.py` (dominio sin BD), `test_application.py` (repositorio en memoria), `test_api.py` (APITestCase con token y PostgreSQL; cubre AC-01..AC-08, EDGE-01..05).
- Frontend: specs del servicio, de lista, formulario y detalle, y `layout/sidebar/sidebar-menu.spec.ts` (AC-09; requirió `"resolveJsonModule": true` en `tsconfig.spec.json`).

**Verificación propia (no es el Quality Gate):** `python manage.py test` → 58 tests OK (44 de `catalog`); `makemigrations --check` sin cambios; `ng lint` y `ng build` OK; los 41 specs nuevos de Angular pasan.

**Desviaciones respecto al plan**
- El precio del formulario es `input type="text" inputmode="decimal"` con validación por patrón (hasta 10 enteros y 2 decimales, acepta coma y la normaliza a punto) en lugar del `type="number"` del DDR: así el valor viaja como string sin pasar por `float`. La Specification (AC-12, UI-02) sigue satisfecha.
- La ruta se declaró directamente como `catalog/products` → `products.routes.ts` (sin archivo intermedio `catalog.routes.ts`).
- `ProductList.onPage` ignora eventos `page` que no cambian de página: ngx-datatable emite `page` al inicializarse y provocaba una petición duplicada.

**Ajustes posteriores a la entrega (pedidos del usuario, sin cambio de Specification)**
- Lista: el selector de estado y el botón "+" se alinean en una fila (`d-flex gap-2`; antes el selector ocupaba todo el ancho y empujaba el botón).
- Acciones de la tabla (`product-list.component.scss`): Ver = color primario de la aplicación (`#6777ef`), Editar = amarillo (`#ffc107`), Desactivar/Activar = rojo (`#dc3545`), con iconos centrados (`inline-flex`, sin relleno). No se agregó botón "Eliminar": el producto solo se desactiva (INV-05); el botón rojo es el de activar/desactivar y es rojo en ambos estados.
- Idioma: la aplicación arranca en español (`DEFAULT_LANGUAGE = 'es'` en `language.service.ts`, `defaultLanguage: 'es'` en `app.config.ts`) en lugar de tomar el del navegador, para que el menú diga "Catálogo". Es un cambio global (afecta a toda la app); respeta el idioma ya elegido en el selector del encabezado. Spec: `language.service.spec.ts`.

**Estado previo del repositorio (no causado por este cambio)**
- `npm test` completo no compila: `src/app/app.component.spec.ts:24` referencia `AppComponent.title`, que no existe. Con ese archivo excluido corrieron 137 specs: 82 fallan en specs de la plantilla ("should create" sin providers: `ActivatedRoute`, `ToastConfig`, iconos feather), incluido `SidebarComponent should create`. Ninguno de esos archivos fue modificado. Hay que decidir si se corrigen en un task aparte; el Quality Gate no podrá usar `npm test` completo hasta entonces.

**Entorno de la verificación:** el worktree no tenía `node_modules` ni `backend/.env`; se enlazaron (junction y hard link) a los del checkout principal, sin leer ni modificar `.env`; ambos están en `.gitignore`.

**Deuda técnica / no verificado**
- No se hizo la verificación manual de humo con backend + `npm start` (queda para `delivery-review`).
- Rutas y componentes de demo siguen accesibles por URL (ADR frontend-feature).

## Review
**Resultado: PASS** (2026-10-08, rama `task/TASK-catalogo-productos-mvp` en `b3660ed`).

Issues abiertos: [REV-2026-10-08-catalogo-productos-mvp-01](../reviews/REV-2026-10-08-catalogo-productos-mvp-01.md) (Low, PLAN: cambio de idioma por defecto fuera del plan v1; no bloquea).

Verificación:
- Backend (ejecutado por el usuario en otro worktree en el mismo commit `b3660ed`; el reviewer no tuvo acceso a la BD): `python manage.py test` → 58 tests OK; `makemigrations --check --dry-run` → sin cambios; `migrate` aplica `catalog.0001_initial`.
- Frontend (ejecutado por el reviewer): `ng lint` OK; `ng build` OK; 44 specs de la funcionalidad OK (cobertura de esos specs: statements 84,5 %, branches 78,4 %, funciones 75 %, líneas 83,5 %). Suite completa: 66 OK / 75 fallos, todos "should create" de specs de la plantilla preexistentes; `app.component.spec.ts` no compila en `main` (excluido).
- Smoke manual (backend + `npm start`): ejecutado por el usuario, sin problemas.
- Límites DDD revisados: `domain/` sin Django; `catalog` no importa otros módulos; vistas delgadas.
- No realizado: `npm audit` (no hay `package-lock.json`); no hay `bandit`/`safety` configurados. Cobertura de backend por revisión manual, no por herramienta.

## Publicación
_Pendiente_
