# TASK-clientes-mvp: Módulo Clientes (crear, editar, buscar, historial, desactivar, duplicados) + menú "Cliente"

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** `task/TASK-clientes-mvp`
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/6

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-08 | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-10-08 | DESIGN → ARCHITECTURE | Decisión de diseño registrada en DDR (menú directo "Cliente"; lista con filtro Activos por defecto; formulario y perfil como páginas; duplicado por diálogo al enviar; historial como sección del perfil) | delivery-design |
| 2026-10-08 | ARCHITECTURE → PLANNING | Decisiones registradas en 4 ADR (módulo `customers`, contrato API con 409 de duplicado, historial vía Sales, feature frontend) | delivery-architect |
| 2026-10-08 | PLANNING → ENGINEERING | Plan v1 COMPLETO, Specification READY; PR abierto | delivery-plan |
| 2026-10-08 | ENGINEERING → REVIEW | Implementación completa según plan v1 (backend `customers`, frontend `features/customers`, menú) | delivery-engineer |
| 2026-10-08 | REVIEW → PLANNING | Review FAIL: REV-01 (High, SPECIFICATION) y REV-03 (Low, SPECIFICATION) requieren plan v2 | delivery-review |
| 2026-10-08 | PLANNING → ENGINEERING | Plan v2 con aprobación del usuario (regla de normalización "ya prefijado", AC-08 acotado); REV-02 queda para implementación | delivery-plan |
| 2026-10-08 | ENGINEERING → REVIEW | Plan v2 implementado (regla de teléfono ya prefijado, serializer sin validar `name`); REV-01, REV-02 y REV-03 atendidos | delivery-engineer |
| 2026-10-08 | REVIEW → PUBLISH | Re-review PASS: REV-01, REV-02 y REV-03 cerrados; 72 tests de clientes y 130 de backend OK en PostgreSQL, frontend 90 specs OK | delivery-review |
| 2026-10-08 | PUBLISH (sin cambio) | PR completado; pendiente de aprobación humana por ser cambio sensible (DB + arquitectura) | delivery-publish |

## Investigación

### Requerimiento
Objetivo: registrar clientes y permitir consultar su historial comercial sin convertir el módulo en un CRM complejo durante el MVP. Pedido adicional del usuario: "esto será el módulo de cliente, crea un menú llamado Cliente".

- **REQ-CUS-001 Crear cliente** (MVP-Alta): desde la gestión de clientes o durante la creación de un pedido. Nombre obligatorio; teléfono y correo opcionales (salvo que el flujo comercial requiera uno); teléfono almacenado normalizado cuando sea posible. Aceptación: se crea con solo nombre; el nuevo cliente puede asociarse de inmediato a un pedido.
- **REQ-CUS-002 Editar cliente** (MVP-Alta, dep. 001): actualizar contacto y notas; no rompe referencias a pedidos anteriores. Aceptación: cambios visibles en el perfil; el historial sigue asociado.
- **REQ-CUS-003 Buscar clientes** (MVP-Alta, dep. 001): búsqueda rápida durante la venta, al menos por nombre y teléfono; coincidencias parciales relevantes.
- **REQ-CUS-004 Historial de compras** (MVP-Media, dep. 001 y REQ-SAL-001): el perfil muestra pedidos (fecha, total, estado). Customers no modifica pedidos; solo consulta lo provisto por Sales.
- **REQ-CUS-005 Desactivar cliente** (MVP-Baja, dep. 001): sin borrado físico con ventas asociadas; el desactivado no aparece por defecto entre activos; sus pedidos históricos siguen accesibles.
- **REQ-CUS-006 Detectar duplicados evidentes** (MVP-Media, dep. 001): advertir al crear con un teléfono ya registrado, comparando el teléfono normalizado; no necesariamente bloquea, puede requerir confirmación.

### Hechos encontrados

**Backend**
- `backend/modules/` contiene `accounts` y `catalog` (rama actualizada a `main` @ `d85f16e`); **no existen `customers` ni `sales`** (`ls backend/modules`). `docs/architecture/ddd.md:228-309` define Customers pero no está implementado.
- `backend/config/settings/base.py:20-21` registra `modules.accounts` y `modules.catalog` en `INSTALLED_APPS`; `backend/config/urls.py:9-10` monta `api/auth/` y `api/products/` (nótese que el DDD sugiere `/api/customers`, `ddd.md:930-937`).
- `backend/config/settings/base.py:70-86` — DRF: Token + Session, `IsAuthenticated` por defecto, solo `JSONRenderer`, `PageNumberPagination` con `PAGE_SIZE: 50`.
- `backend/requirements/base.txt:1-4` — solo Django, DRF, psycopg, django-environ. **No hay librería de teléfonos** (ni `phonenumbers` en backend ni nada similar en `frontend/panel_admin/package.json`; grep sin resultados). Ningún código existente menciona "phone/teléfono" en `backend/`.
- Patrón de referencia ya implementado (`catalog`): `domain/product.py:46-70` (dataclass sin Django, `Product.create`, validadores `validate_name`/`validate_price`, errores por campo vía `ProductValidationError`), `domain/repositories.py`, `application/{commands,queries}.py`, `infrastructure/django/{models,mappers,repositories}.py`, `api/{serializers,views,urls,pagination}.py`, tests en `tests/test_{domain,application,api}.py`.
- `backend/modules/catalog/infrastructure/django/models.py:6-17` — modelo con UUID PK, `created_at`/`updated_at`, `db_table = 'catalog_product'`, `ordering = ['name','id']`; `infrastructure/django/repositories.py:41-44` — búsqueda con `name__icontains`; `api/pagination.py:4-6` — `page_size` máx. 100; `api/urls.py:10-15` — rutas con `<uuid:product_id>/` y acciones `activate/` y `deactivate/`.
- Última migración de negocio: `backend/modules/catalog/migrations/0001_initial.py` (customers tendría su propia `0001`).
- `backend/shared/` solo tiene `__init__.py`; `PhoneNumber` y `EmailAddress` como Value Objects están descritos en `ddd.md:263-281` pero no existen.

**Reglas de dominio ya documentadas (`ddd.md`)**
- `:240-250` Customer: `id, name, phone, email, notes, created_at, updated_at`; futuros opcionales: `birthdate, preferred_channel, address, tags` (`:252-259`).
- `:263-281` Value Objects: `PhoneNumber` (ejemplo `+591 7xxxxxxx`) y `EmailAddress`.
- `:283-288` Reglas: puede existir sin email; el teléfono puede ser identificador práctico (WhatsApp); no eliminar clientes con historial; preferir desactivación o anonimización.
- `:294-309` Commands `CreateCustomer, UpdateCustomer, DeactivateCustomer`; Queries `GetCustomer, SearchCustomers, ListCustomers, GetCustomerPurchaseHistory`.
- `:340-347` y `:772-779` Sales referencia `customer_id`; no debe manipular los modelos internos de Customers. `:543` Sales expone `ListOrdersByCustomer`. `:741-742` Reporting solo lee.
- `:930-937` endpoints sugeridos: `GET/POST /api/customers`, `GET/PATCH /api/customers/{id}` (sin `deactivate`/`activate` ni historial).
- `:1050-1060` Angular: `features/customers/{pages/customer-list, pages/customer-detail, components, services, models}`.
- `:880-912` el propio DDD dice que separar modelos Django y entidades no es obligatorio en el MVP salvo dominios con lógica relevante.

**Ventas (dependencia de REQ-CUS-001 criterio 2, 004 y 005)**
- No hay módulo `sales`, ni `Order`, ni endpoint de pedidos (`ls backend/modules`, `backend/config/urls.py:6-11`). `ddd.md:545` / `:543` solo describen `ListOrdersByCustomer` como caso de uso futuro. Por tanto hoy no hay pedidos que asociar, consultar ni que impidan borrar.

**Frontend**
- `frontend/panel_admin/src/app/features/` contiene solo `products/` (pages `product-list`, `product-form`, `product-detail`; `services/products-api.service.ts`; `models/product.ts`; `products.routes.ts`; `testing/product-fixtures.ts`).
- `frontend/panel_admin/src/app/features/products/products.routes.ts:7-11` — rutas `''`, `new`, `:id/edit`, `:id`; registrada en `app.routes.ts:20-22` como `catalog/products` con `loadChildren`.
- Menú: `frontend/panel_admin/src/assets/data/routes.json:1-38` — hoy solo "Dashboard" y "Catálogo ▸ Producto" (`icon: package`, `class: menu-toggle`, submenú `class: ml-menu`); títulos por claves `MENUITEMS.*` en `src/assets/i18n/{en,es,de}.json` (`es.json:7-19`, sección `MENUITEMS` con `CATALOG`).
- Lista de productos: `ngx-datatable class="material"` con paginación externa (`product-list.component.html:57-58`), buscador con debounce, filtro de estado, confirmación `Swal` + `toastr` (según TASK del catálogo, sección Implementación).
- Idioma por defecto de la app: español (cambio hecho en el task del catálogo, `language.service.ts` / `app.config.ts`).
- Autenticación: el interceptor añade `Authorization: Token <token>` a URLs de `environment.apiUrl` (`/api`); `proxy.conf.json` → `http://127.0.0.1:8000`.
- No existe pantalla de pedidos ni selector de cliente en un pedido (no hay `features/sales`).

### Hipótesis / supuestos no confirmados
- "Menú llamado Cliente" se interpreta como una entrada de menú lateral (probablemente con submenú o entrada directa a la lista de clientes, siguiendo el patrón de "Catálogo ▸ Producto"); no se confirmó si es entrada directa "Cliente" o grupo con submenú, ni si el texto es "Cliente" o "Clientes".
- REQ-CUS-001 criterio 2 ("asociarse inmediatamente a un pedido") y REQ-CUS-004 (historial) dependen de REQ-SAL-001, que no existe. Se asume que en este task solo se puede dejar listo el contrato de Customers (identificador estable y consulta), no probar la asociación/historial extremo a extremo; no confirmado qué alcance espera el usuario (¿incluye una pestaña de historial vacía/placeholder, o un puerto/interfaz que Sales implementará?).
- "Normalizar teléfono" requiere elegir una regla (p. ej. prefijo `+591` Bolivia por el ejemplo de `ddd.md:271-273`, uso de librería tipo `phonenumbers` o normalización propia a dígitos); el requisito dice "cuando sea posible", lo que implica aceptar números no normalizables. Esa decisión no está tomada y puede implicar una dependencia nueva (CLAUDE.md exige avisar).
- Se asume que "desactivar" sigue el mismo patrón que `catalog` (`active`, endpoints `activate/deactivate`), y que reactivar está permitido; no confirmado (REQ-CUS-005 solo menciona desactivar).
- Se asume que el flag de duplicado se resuelve en el backend (respuesta de advertencia + confirmación explícita para crear igualmente), pero la forma del contrato (409 con coincidencias, parámetro `confirm`, endpoint de verificación previa) no está definida.
- Búsqueda: se asume paginación en servidor con `search` por nombre y teléfono como en catálogo; no confirmado si el buscador de venta (en pedidos) reutiliza el mismo endpoint ni si debe buscar por teléfono parcial normalizado.
- No se confirmó si el teléfono debe ser único a nivel de base de datos (el requisito pide advertir, no bloquear, así que una restricción única parece contradecir REQ-CUS-006).
- No se confirmó si hay límites de longitud para nombre/teléfono/correo/notas ni si el correo debe validarse (ddd.md menciona `EmailAddress` como VO que "valida").
- No se verificó el contenido de la base de datos ni migraciones aplicadas localmente.

### Módulos y dependencias relacionadas
- **Backend:** nuevo bounded context `customers` (capas `domain/application/infrastructure/api`, creadas solo si hacen falta, `CLAUDE.md`); registro en `INSTALLED_APPS` y `config/urls.py`; migración inicial. Dependencia entrante futura: `sales` referencia `customer_id` por id/servicio de aplicación, nunca por modelos (`ddd.md:772-807`); `reporting` solo lee (`:741`). **Dependencia saliente de REQ-CUS-004:** Customers necesita datos de pedidos que provee Sales (módulo inexistente), lo cual invertiría la dirección sugerida en `ddd.md:757-770` (Customers ← Sales) si se resuelve con una llamada directa de Customers a Sales.
- **Frontend:** nueva carpeta `features/customers/` (`ddd.md:1050-1060`), `app.routes.ts`, `assets/data/routes.json` y `assets/i18n/{en,es,de}.json` (menú "Cliente").
- **Cruza límites de módulo:** potencialmente sí (historial de compras depende de Sales; asociación a pedido depende de Sales), aunque hoy Sales no existe.

### Implementaciones similares existentes
- `catalog` (backend completo) y `features/products` (frontend completo, con specs): es el patrón que el módulo de clientes debería seguir (crear/editar/consultar/listar con búsqueda y filtro de estado/activar-desactivar). Ver ADRs `docs/adr/ADR-catalogo-productos-mvp-{modelo-dominio,contrato-api,frontend-feature}.md` y `docs/design/DDR-catalogo-productos-mvp-menu-y-pantallas-producto.md` (decisiones ya tomadas para un recurso análogo).
- No existe precedente de: normalización de datos de contacto, detección de duplicados con advertencia/confirmación, endpoint de consulta cruzada entre módulos, ni de un selector/creación en línea de una entidad desde otro flujo (el "crear durante un pedido").

### Comportamiento actual
- No existe ninguna pantalla, endpoint ni modelo de clientes. `GET /api/customers/` devolvería 404 (no está en `backend/config/urls.py:6-11`). El menú lateral no tiene entrada "Cliente" (`routes.json:1-38`).
- El catálogo de productos funciona como referencia operativa (lista paginada en servidor, alta/edición/detalle, activar/desactivar, tests).

### Restricciones
- `CLAUDE.md`: cambios acotados a un objetivo y **plan + confirmación antes de tocar varios archivos**; dinero en `Decimal` (no aplica directamente aquí); nunca editar migraciones aplicadas; no leer/modificar `.env`; **avisar antes de instalar dependencias** (relevante si se usa una librería de teléfonos); dominio sin imports de Django; módulos no se importan infraestructura entre sí; Reporting solo lee; estados cambian por métodos del agregado; no agregar abstracciones DDD sin necesidad real; frontend por `features/<modulo>/`, tipos explícitos sin `any`, Reactive Forms, sin suscripciones colgadas; una rama y un PR por task (`task/TASK-<slug>`).
- Fuera del MVP (`CLAUDE.md`, `ddd.md:1205-1222`): microservicios, event sourcing, CQRS completo, inventario/producción avanzados. El objetivo del requisito excluye explícitamente convertir el módulo en un CRM complejo (campos futuros de `ddd.md:252-259` no aplican al MVP).
- Reglas de negocio de los REQ: nombre obligatorio; teléfono/correo opcionales; teléfono normalizado "cuando sea posible"; no borrado físico de clientes con ventas; duplicado por teléfono normalizado = advertencia/confirmación, no bloqueo necesariamente.

### Riesgos identificados
- **Dependencia de Sales inexistente:** REQ-CUS-001 (asociar a pedido), REQ-CUS-004 (historial) y parte de REQ-CUS-005/002 (histórico accesible, no romper referencias) no son verificables extremo a extremo sin REQ-SAL-001; riesgo de entregar contratos que luego Sales no pueda cumplir o de acoplar Customers a Sales en la dirección equivocada.
- **Normalización de teléfono:** sin precedente ni librería; riesgo de reglas ad hoc inconsistentes (prefijo país, espacios, guiones), de nueva dependencia, y de que la comparación de duplicados falle si los datos existentes no están normalizados de la misma forma.
- **Detección de duplicados sin bloqueo:** el contrato (cómo se comunica la advertencia y cómo se confirma) no tiene precedente y afecta al frontend de clientes y al flujo de creación en pedidos; una restricción única en BD contradiría el requisito.
- **Segundo bounded context:** consolida el patrón de `catalog` (entidad pura + repositorio + mapper); desviarse crea inconsistencia entre módulos.
- **Creación desde un pedido:** exige un componente/flujo de creación rápida reutilizable (modal o selector) fuera de `features/customers`, lo que roza la frontera entre features en Angular.
- **Plantilla y suite de tests:** el task del catálogo documenta que la suite completa de Angular tiene specs de plantilla fallando y `app.component.spec.ts` sin compilar en `main`; la verificación de la nueva funcionalidad debe acotarse a sus propios specs.
- **Datos personales:** teléfono, correo y notas son datos personales; `ddd.md:287-288` menciona anonimización, sin definición para el MVP.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — Se crea un nuevo bounded context (`customers`) con modelo de BD y migración, y hay decisiones con impacto entre módulos (cómo Customers consulta/expone historial a partir de Sales, contrato de `customer_id` para pedidos, normalización de teléfono y contrato de advertencia de duplicados) que condicionan a Sales y Reporting.

### Diseño requerido
**SI** — Hay pantallas nuevas (lista con búsqueda y filtro de estado, formulario de alta/edición, perfil con historial), un nuevo ítem de menú "Cliente", y flujos que requieren decisión de UX: advertencia/confirmación de duplicado, creación rápida desde un pedido y presentación del historial cuando Sales aún no existe.

## Diseño
- [DDR-clientes-mvp-menu-y-pantallas-cliente](../design/DDR-clientes-mvp-menu-y-pantallas-cliente.md) — Propuesto. Reutiliza el patrón de `features/products`. Menú: entrada directa "Cliente" (`/customers`); lista con búsqueda por nombre/teléfono y estado "Activos" por defecto; formulario y perfil como páginas con URL; advertencia de duplicado con `Swal` al enviar (no bloquea); historial (fecha, total, estado) como sección del perfil. Creación rápida desde pedido: solo diseñada, se construye con Sales.
- Pendiente para arquitectura: normalización de teléfono (¿librería nueva?), contrato de duplicado, fuente del historial desde Sales, activar/desactivar, búsqueda por nombre/teléfono.

## Arquitectura
- [ADR-clientes-mvp-modelo-dominio](../adr/ADR-clientes-mvp-modelo-dominio.md) — módulo `customers` con entidad `Customer` de dominio puro (patrón de `catalog`); normalización de teléfono propia (`+<país><dígitos>`, país por defecto `591` vía setting, no normalizable se guarda tal cual); duplicado por igualdad del teléfono normalizado, índice no único; búsqueda nombre/teléfono; sin borrado.
- [ADR-clientes-mvp-contrato-api](../adr/ADR-clientes-mvp-contrato-api.md) — `/api/customers/` (lista con `search`/`active`/paginación, alta, detalle, PATCH, `activate`/`deactivate`, sin DELETE); duplicado en el alta → `409 {code: duplicate_phone, matches}` y reenvío con `confirm_duplicate: true`; PATCH no comprueba duplicados.
- [ADR-clientes-mvp-historial-compras](../adr/ADR-clientes-mvp-historial-compras.md) — el historial lo provee Sales (`GET /api/orders/?customer_id=`); Customers no importa Sales; el perfil trae la sección con estado vacío; REQ-CUS-004 y la asociación a pedido se cierran con el task de Sales.
- [ADR-clientes-mvp-frontend-feature](../adr/ADR-clientes-mvp-frontend-feature.md) — `features/customers`, rutas `customers*`, menú directo; `Page<T>` y estilos de acciones duplicados (sin importar de `products`).
- Sin dependencias nuevas; cambios aditivos con rollback por revert de PR / `migrate customers zero`. Supuesto a confirmar: código de país por defecto `591`.

## Plan
- [PLAN-2026-10-08-clientes-mvp](../plans/PLAN-2026-10-08-clientes-mvp.md) — v2 (antes v1), Modo COMPLETO, Specification readiness: READY. 13 ACs (API, menú, lista, formulario, duplicado, perfil), 7 invariantes, sin dependencias nuevas, E2E: NO (verificación manual de humo).
- **v2 (2026-10-08):** cambios de Specification aprobados por el usuario: AC-03/EDGE-02 (dígitos con código de país ya incluido se toman como prefijados) y AC-08 (404 sin `{detail}` para ids que no son UUID). Resuelve REV-01 y REV-03; REV-02 (IMPLEMENTATION, AC-02/EDGE-10) se corrige en implementación. ADR modelo-dominio enmendado.
- Pregunta abierta no bloqueante: código de país por defecto `591` (configurable con `DEFAULT_PHONE_COUNTRY_CODE`). REQ-CUS-004 (historial real) y la asociación a pedido se cierran con el task de Sales.

## Implementación
Rama `task/TASK-clientes-mvp`, PR #6, siguiendo el plan v1 (COMPLETO).

**Backend** (`backend/modules/customers/`)
- `domain/` — `Customer` (dataclass sin Django) con `create`, `rename`, `change_contact`, `change_notes`, `activate`, `deactivate`; `normalize_phone` y validadores; `CustomerValidationError`, `CustomerNotFound`, `CustomerRepository` (Protocol con `find_by_phone`): INV-01..05, INV-07, AC-02, AC-03.
- `application/` — `CreateCustomer` (consulta duplicados y lanza `DuplicateCustomerPhone` salvo `confirm_duplicate`), `UpdateCustomer` (parcial, junta errores, no guarda sin cambios, no comprueba duplicados), `ActivateCustomer`, `DeactivateCustomer`, `GetCustomer`, `ListCustomers`: AC-01, AC-04, AC-05, AC-07, INV-06.
- `infrastructure/django/` — `CustomerModel` (UUID, `phone` con índice **no** único, tabla `customers_customer`), mapper, `DjangoCustomerRepository` (lista perezosa; búsqueda `name__icontains` o dígitos del término en `phone`; `find_by_phone`); `migrations/0001_initial.py` generada con `makemigrations`: AC-06.
- `api/` — serializers, vistas `APIView` delgadas (`_run` traduce dominio→400/404; el duplicado se devuelve como `Response` 409 directa), `CustomerPagination` (máx. 100), urls; montado como `api/customers/` en `config/urls.py`, app en `INSTALLED_APPS`, setting `DEFAULT_PHONE_COUNTRY_CODE` (env, por defecto `591`) y variable documentada en `.env.example`: AC-01..AC-08, API-01.

**Frontend** (`frontend/panel_admin/src/app/features/customers/`)
- `models/customer.ts`, `services/customers-api.service.ts` (DTO snake_case ↔ modelo, 400→errores por campo, 409 `duplicate_phone`→`DuplicateCustomerError`, `create(input, confirmDuplicate)`).
- `pages/customer-list` (Activos por defecto, búsqueda única con debounce, paginación en servidor, confirmación `Swal` + `toastr`), `pages/customer-form` (alta/edición tipado, diálogo de duplicado con nombres escapados y reintento con confirmación), `pages/customer-detail` + `components/customer-purchase-history` (sección vacía, **sin ninguna petición a pedidos**); `customers.routes.ts` y ruta `customers` en `app.routes.ts`: AC-10..AC-13.
- Menú: entrada directa "Cliente" en `routes.json` (ícono `users`) y claves `MENUITEMS.CUSTOMER.TEXT` en en/es/de: AC-09. `sidebar-menu.spec.ts` actualizado a 3 entradas y 4 títulos.
- Docs: `ddd.md` (endpoints `activate`/`deactivate` de clientes) y `CLAUDE.md` (variable opcional).

**Tests escritos**
- Backend: `test_domain.py` (SimpleTestCase, tabla de `normalize_phone`), `test_application.py` (repositorio en memoria), `test_api.py` (APITestCase con token; AC-01..AC-08, EDGE-01..09).
- Frontend: specs del servicio, de lista, formulario (incl. flujo de duplicado y escape HTML), perfil, sección de historial y `sidebar-menu.spec.ts`.

**Verificación propia (no es el Quality Gate):**
- `python manage.py test modules.customers` → 68 tests OK, **ejecutados con SQLite en memoria** (`DATABASE_URL=sqlite:///:memory:`) porque este worktree no tiene `backend/.env` y no se leyó el `.env` del checkout principal. **No se corrieron contra PostgreSQL**; hay que repetirlo allí. Suite completa con SQLite: 126 tests, 1 falla preexistente de `catalog` (`test_orders_by_name_and_filters`, orden por mayúsculas/minúsculas dependiente de la collation de SQLite).
- `makemigrations --check --dry-run` → sin cambios pendientes.
- `ng lint` OK; `ng build` OK; 51 specs (clientes + sidebar) OK y 39 specs de `features/products` OK, ejecutados con un `tsconfig` temporal (ya borrado) que excluye `app.component.spec.ts`, que no compila en `main` (preexistente).

**Desviaciones respecto al plan**
- **Ejemplo de AC-03:** el plan lista `(591) 76543210` como normalizable a `+59176543210`, pero la regla del plan y del ADR (sin `+` ni `00` y solo dígitos, antepone el país) lo convertiría en `+59159176543210`. Se implementó la **regla** tal cual; el ejemplo es un error de redacción del AC y los tests usan `+(591) 76543210`. Conviene corregir el texto del AC-03 en el plan (no cambia comportamiento).
- Los tests de API usan nombres con inicial mayúscula en todos los casos para no depender de la collation de la base de datos al ordenar.
- El correo se valida en el formulario sobre el valor recortado (validador propio en lugar de `Validators.pattern`) para que un espacio al final no deshabilite Guardar.
- Tras crear un cliente la UI navega a su perfil (AC-11), a diferencia de productos, que vuelve a la lista.

**Deuda técnica / no verificado**
- Tests de API no ejecutados en PostgreSQL; sin humo manual con backend + `npm start` (queda para `delivery-review`).
- Duplicados: `Page<T>` y los estilos de acciones de tabla están copiados de `products` (ADR frontend-feature); extraer a `shared/` cuando haya una tercera feature.
- REQ-CUS-004 (historial real) y la asociación a pedido dependen de Sales; el código de país `591` sigue sin confirmar.

### Iteración 2 (plan v2, tras el review FAIL)
- **REV-01 / AC-03, EDGE-02** — `normalize_phone` (`domain/customer.py`): un número de solo dígitos que ya empieza con el código de país y deja 8 o más dígitos se toma como prefijado; `591 76543210`, `(591) 76543210` y `59176543210` → `+59176543210`; `59176543` → `+59159176543`. Tests: tabla de dominio ampliada y, en API, todos los formatos del mismo número dan 409 (`test_all_formats_of_the_same_number_are_duplicates`).
- **REV-02 / AC-02, EDGE-10** — `CustomerInputSerializer`: `name` pasa a `CharField(required=False, allow_blank=True)` sin `max_length`; la vista del alta envía `name=None` si falta, y el dominio devuelve "El nombre es obligatorio." junto con los errores de los demás campos. Test: `test_invalid_name_is_reported_together_with_other_fields`.
- **REV-03 / AC-08** — sin cambio de código: el texto del AC quedó acotado; el test de ids ahora comprueba además el cuerpo `{detail}` de un UUID válido inexistente.
- La desviación "ejemplo de AC-03" de la iteración 1 queda resuelta por el plan v2. Los tests ya usan `(591) 76543210` sin `+`.
- Verificación propia: `python manage.py test modules.customers` → 72 OK con SQLite en memoria (no PostgreSQL); el frontend no cambió en esta iteración.

## Review
**Resultado: PASS** (re-review 2026-10-08 sobre `58e1784`, plan v2; sesión sin aislamiento real de memoria respecto de otras skills `delivery-*`).

Issues de la primera revisión, todos cerrados:
- [REV-01](../reviews/REV-2026-10-08-clientes-mvp-01.md) (High, SPECIFICATION) — regla "ya prefijado" aprobada y aplicada: `591 76543210`, `(591) 76543210`, `59176543210` → `+59176543210` y se detectan como duplicados (409 verificado en servidor real); `59176543` sigue siendo local.
- [REV-02](../reviews/REV-2026-10-08-clientes-mvp-02.md) (Low, IMPLEMENTATION) — `name` inválido + otros campos → un solo 400 con todos y mensaje de dominio.
- [REV-03](../reviews/REV-2026-10-08-clientes-mvp-03.md) (Low, SPECIFICATION) — AC-08 acotado; UUID inexistente devuelve `{"detail":"Cliente no encontrado."}`.

Verificación ejecutada (detalle en el PR, `## Testing`): backend en PostgreSQL `modules.customers` 72 OK y suite completa 130 OK; `makemigrations --check` sin cambios; `bandit` 0 issues; límites DDD OK; humo de API en servidor real con base desechable (borrada); `ng lint` OK; `ng build` OK; 90 specs (clientes + sidebar + productos) OK, cobertura statements 95.6 % · branches 84.78 % · functions 92.62 % · lines 95.54 %. El frontend no cambió desde la primera revisión.

No realizado (consta explícitamente): `npm audit` (sin lockfile, `ENOLOCK`); `flake8`/`ruff`/`mypy` (no configurados); humo de UI en navegador (el proxy de `npm start` apunta a `127.0.0.1:8000`, ocupado por el backend del usuario; AC-09..AC-13 cubiertos por specs de componentes). Se recomienda un humo manual del flujo menú → crear → duplicado → confirmar → editar → buscar → desactivar antes de fusionar.

Pendientes aceptados del plan: código de país `591` sin confirmar con el negocio; REQ-CUS-004 (historial real) y asociación a pedido se cierran con Sales.

Siguiente paso: `/delivery-publish TASK-clientes-mvp`.

## Publicación
- PR: https://github.com/rolion/dore-mini-erp/pull/6 — descripción completa (Summary, Architecture decisions, Known limitations).
- Estado: **Listo para aprobación humana** (no mergeado). Cambio sensible: base de datos (migración `customers.0001_initial`) y arquitectura (4 ADR: módulo `customers`, contrato API, historial vía Sales, feature frontend); requiere aprobación explícita antes del merge.
- Antes de fusionar: humo manual de UI (menú → crear → duplicado → confirmar → editar → buscar → desactivar) y, tras el merge, `python manage.py migrate` en cada entorno.
