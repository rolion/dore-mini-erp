# TASK-registro-usuarios-empresa-multitenant: Registro de usuarios con empresa y aislamiento de datos por empresa

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** `task/TASK-registro-usuarios-empresa-multitenant`
**Pull Request:** _sin abrir todavía_

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-12 | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-10-12 | DESIGN → ARCHITECTURE | DDR de pantalla de registro y señales de empresa en el header; veredicto NEEDS_ARCHITECTURE | delivery-design |
| 2026-10-12 | ARCHITECTURE → PLANNING | 3 ADR: aislamiento por columna company_id, empresa derivada de la sesión y propagada por repositorios/fachadas, registro público que crea empresa + rol admin. Decisión de negocio del usuario: nombre de empresa existente se rechaza; usuarios adicionales los agrega el admin | delivery-architect |
| 2026-10-12 | PLANNING → ENGINEERING | Plan v1 COMPLETO, Specification READY; PR abierto | delivery-plan |

## Investigación

### Requerimiento
Tal como se recibió:

> necesitamos registrar a los usuarios, la plantilla tiene un formulario de sign up, reusémoslo, agrega el campo nombre de empresa, es requerido.
> Todo usuario tiene acceso a los datos de su empresa y solo de su empresa.
> Hay que ajustar las llamadas api para incluir el nombre de empresa y filtrar todos los datos por ese nombre.
> Cada usuario tiene un o grupo de admin; por el momento el admin tiene acceso a todo el sistema y puede ver, leer, modificar o dar de alta los datos de su empresa.

Cuatro partes: (1) registro de usuarios desde el formulario sign-up de la plantilla con `nombre de empresa` obligatorio; (2) aislamiento de datos por empresa para todo usuario; (3) las llamadas API incluyen/filtran por el nombre de empresa; (4) rol/grupo "admin" con acceso total a los datos de su empresa.

### Hechos encontrados

**Backend — usuarios y autenticación**
- `backend/modules/accounts/models.py:4-6` — `User(AbstractUser)` vacío ("usuario propio mínimo"). No tiene campo de empresa ni de rol. `AUTH_USER_MODEL = 'accounts.User'` en `backend/config/settings/base.py:28`.
- `backend/modules/accounts/migrations/0001_initial.py` — única migración de `accounts`; la siguiente sería `0002`.
- `backend/modules/accounts/api/urls.py:5-8` y `views.py:14-41` — solo existen `POST /api/auth/login/` y `/logout/`. **No hay endpoint de registro.**
- `backend/modules/accounts/api/serializers.py:11-15` — `UserSerializer` expone `id, username, first_name, last_name` (sin empresa ni rol).
- `backend/modules/accounts/api/views.py:32` — login devuelve `{token, user}`; token DRF (`rest_framework.authtoken`).
- `backend/config/settings/base.py:78-94` — DRF: `TokenAuthentication` + `SessionAuthentication`, permiso por defecto `IsAuthenticated`, throttle solo para el scope `login` (`10/min`).
- No existe ningún uso de `Group`, `permission`, `is_staff`, `is_superuser` ni `has_perm` en el código del backend (grep sobre `backend/`, excluyendo migraciones y `rest_framework.permissions`). No hay noción de roles.
- No hay middleware ni mixin que ponga datos de usuario/empresa en el contexto de la petición (`base.py:30-38` solo trae los middlewares estándar de Django).

**Backend — ningún dato tiene dueño (empresa)**
- `catalog/infrastructure/django/models.py:6-17` (`ProductModel`), `customers/infrastructure/django/models.py:6-19` (`CustomerModel`), `sales/infrastructure/django/models.py:7-71` (`OrderModel`, `OrderItemModel`, `PaymentModel`), `expenses/infrastructure/django/models.py:8-44` (`ExpenseCategoryModel`, `ExpenseModel`): ninguno tiene campo de empresa/propietario/usuario. Hoy todos los datos son globales.
- `expenses/infrastructure/django/models.py:19-21` — `ExpenseCategoryModel` tiene una `UniqueConstraint(Lower('name'))` **global**; con varias empresas dos empresas no podrían tener una categoría "Empaque".
- Las referencias entre módulos son solo por UUID sin FK (`sales/infrastructure/django/models.py:9-10`, `product_id` en `:41`).
- Migraciones actuales: `catalog/0001_initial.py`, `customers/0001_initial.py`, `sales/0001_initial.py`, `expenses/0001_initial.py`; `reporting` no tiene modelos ni migraciones.

**Backend — dónde se leen/escriben los datos (puntos que hoy no reciben contexto de empresa)**
- Repositorios (sin parámetro de usuario/empresa; consultan `Model.objects` completo):
  - `catalog/infrastructure/django/repositories.py:33-47` (`get`, `save`, `list`).
  - `customers/infrastructure/django/repositories.py:35-59` (`get`, `save`, `list`, `find_by_phone` — esta última detecta teléfono duplicado sobre **todos** los clientes).
  - `sales/infrastructure/django/repositories.py:39-93` (`get`, `get_for_update`, `save`, `list`).
  - `expenses/infrastructure/django/repositories.py:42-111` (`_filtered`, `DjangoExpenseRepository`, `DjangoExpenseCategoryRepository` incluyendo `find_by_name` y `get_many`).
- Los views instancian los repositorios sin argumentos: p. ej. `catalog/api/views.py:44,52,58,64`, `customers/api/views.py:58,66,76,83`, `sales/api/views.py:87` (`return DjangoOrderRepository()`).
- Las fachadas entre módulos consultan por id sin contexto de empresa: `catalog/services.py:20-28` (`get_product_for_sale`), `customers/services.py:20-36` (`get_customer_for_sale`, `get_customer_names`), usadas por Sales vía `sales/infrastructure/adapters.py:16-32`. Por tanto, un pedido podría referenciar el UUID de un producto/cliente de otra empresa si no hay filtro.
- Consultas de solo lectura para reportes: `sales/infrastructure/django/read_queries.py:16-82` (`valid_orders`, `totals`, `by_channel`, `product_totals`, `customer_totals`, `pending_delivery`, `pending_collection`), expuestas por `sales/services.py:69-121`; `expenses/services.py:34-51` (`get_expense_report`, usa `ExpenseModel.objects` directo). Reporting las consume vía `reporting/infrastructure/adapters.py:27-62` y los views en `reporting/api/views.py:20-40`. Ninguna función de fachada acepta contexto de empresa.
- Paginadores y filtros de API no mencionan empresa: `catalog/api/pagination.py`, `sales/api/filters.py`, `expenses/api/filters.py`.

**API — rutas actuales** (`backend/config/urls.py:8-18`): `/api/products/`, `/api/customers/`, `/api/orders/`, `/api/expenses/`, `/api/expense-categories/`, `/api/reports/`, `/api/auth/`. Ninguna incluye empresa en la ruta ni en query params; todas están protegidas por `IsAuthenticated` (por defecto) salvo login.

**Frontend**
- `frontend/panel_admin/src/app/authentication/signup/signup.component.ts:23-48` — formulario de la plantilla con `fname`, `lname`, `email`, `password`, `termcondition`; `onSubmit()` valida y no hace nada más (`// register user call here..`, línea 46). **No hay campo de empresa ni llamada al backend.** Usa `UntypedFormBuilder` (no tipado).
- `signup.component.html:64-135` — plantilla en inglés ("First name", "Your Email", "Register"), incluye bloque "Or Signup With" con iconos sociales (`:113-129`) y enlace a `/authentication/signin` (`:132`). Rutas de auth: `authentication/auth.routes.ts:15-18` ya expone `signup`.
- `signup.component.spec.ts:5-25` — solo un test "should create".
- Sign in ya integrado con el backend: `core/service/auth.service.ts:29-48` (`login(username, password)`), `core/models/user.ts:1-17` (`User` y `LoginResponse` sin empresa/rol), token en `LocalStorageService` (`auth.service.ts:41`).
- El login usa **`username`**, mientras el formulario de sign-up de la plantilla pide **email** y no pide username (ver `signup.component.ts:25-30` vs. `auth.service.ts:29-31` y `accounts/api/serializers.py:6-8`).
- Interceptor que añade `Authorization: Token ...` solo a la API propia: `core/interceptor/jwt.interceptor.ts` (exportado como `tokenInterceptor`, referenciado en `interceptors.spec.ts:44`); `error.interceptor.ts:11-24` limpia sesión ante 401.
- Servicios de API por feature, todos con `baseUrl = ${environment.apiUrl}/<recurso>/` y sin empresa: `features/products/services/products-api.service.ts:77`, `customers/services/customers-api.service.ts:92`, `customer-orders-api.service.ts:34`, `sales/services/orders-api.service.ts:169`, `expenses/services/expenses-api.service.ts:52`, `categories-api.service.ts:18`, `reporting/services/reporting-api.service.ts:119`.
- `app.routes.ts:7-13` — todo el layout principal está tras `AuthGuard`; `auth.guard.ts:11-17` solo comprueba token. No hay guards por rol.
- `frontend/` **sí está versionado** en este worktree (815 archivos en `git ls-files frontend`).

**Arquitectura / documentación**
- `docs/architecture/ddd.md:1253` — lista **"Multiempresa compleja"** entre las "Funcionalidades que NO deberían entrar inicialmente" (sección 24). `CLAUDE.md` repite "Fuera del MVP: ... " sin mencionar multiempresa explícitamente.
- `docs/architecture/ddd.md:817-819` — convención de fachadas `services.py` y mapa de dependencias entre módulos (`sales → {catalog, customers}`, `reporting → {sales, expenses, customers}`), verificado por `sales/tests/test_boundaries.py`.
- `accounts` existe como app (`modules/accounts`) pero **no figura** en la lista de módulos de negocio de `CLAUDE.md` ni de `ddd.md` (`catalog, customers, sales, expenses, reporting`) y tiene estructura plana (`models.py`, `api/`, sin `domain/application/infrastructure`).
- Tests existentes por módulo: `accounts/tests.py`, `catalog|customers|sales|expenses|reporting/tests/` (`test_api`, `test_application`, `test_domain`, `test_repository`, `test_services`, `fakes.py`). Un cambio de firma en repositorios/fachadas afecta a todos.
- Alta de usuarios hoy: solo `python manage.py createsuperuser` (según `CLAUDE.md`, sección Comandos).

### Hipótesis / supuestos no confirmados
- "nombre de empresa" se interpreta como un **atributo del usuario/entidad Empresa** que se **crea o se reutiliza** al registrarse; no está confirmado si cada registro crea una empresa nueva o se une a una existente por nombre (ver preguntas abiertas).
- Se asume que el filtrado "por ese nombre" es una forma de decir "por la empresa del usuario autenticado" (derivada del token), no que el cliente elija libremente la empresa en cada llamada; permitir que el cliente envíe el nombre en cada petición sería inseguro (cualquier usuario podría leer otra empresa). No confirmado con el solicitante.
- "un o grupo de admin" se lee como "cada usuario tiene un rol; existe el rol/grupo admin". No se confirmó si es un rol único o puede haber otros roles futuros (solo `admin` por ahora).
- Se asume que los datos existentes (si los hay en entornos de desarrollo) pueden asignarse a una empresa por defecto o descartarse; no se verificó si hay datos reales en producción (el proyecto está "en construcción").
- Se asume que `frontend/` y `backend/` se despliegan juntos; no se verificó si existe otro cliente de la API.
- Se desconoce si el registro debe ser público (`AllowAny`) o solo operado por un admin de una empresa existente; no está definido.

### Módulos y dependencias relacionadas
- **Backend:** `accounts` (usuarios, auth, nuevo registro/empresa/rol) y, por el aislamiento, **todos** los módulos de negocio: `catalog`, `customers`, `sales`, `expenses`, `reporting` (capas `infrastructure` — modelos, repositorios, read_queries —, `application` — casos de uso/puertos — y `api` — views; las fachadas `services.py` cruzan módulos).
- **Frontend:** `authentication/signup`, `core/service/auth.service.ts`, `core/models/user.ts`, interceptores en `core/interceptor/`, y los 7 servicios de API de `features/*/services/` si el contrato cambia; potencialmente guards de ruta.
- **Contrato API:** cualquier cambio de payload/ruta/respuesta afecta a todos los servicios del frontend y a sus specs.

### Implementaciones similares existentes
- Patrón de casos de uso + repositorio inyectado + `_run` que traduce excepciones de dominio a HTTP en cada módulo (`catalog/api/views.py:22-29`, `customers/api/views.py:25-32`): un posible punto de entrada para pasar contexto de empresa, ya que todos los views construyen el repositorio en un mismo lugar.
- Patrón de throttle por scope en el login (`accounts/api/views.py:18-19`, `base.py:91-93`): precedente para proteger un endpoint de registro público.
- Patrón de `LazyList`/`*List` y paginación (`catalog/infrastructure/django/repositories.py:11-29`) que envuelve un queryset: el filtrado por empresa tendría que aplicarse antes de ese wrapper.
- No existe ningún patrón previo de multi-tenancy, roles ni permisos por objeto en el repo.

### Comportamiento actual
- Cualquier usuario autenticado (token válido) ve y modifica **todos** los productos, clientes, pedidos, pagos, gastos y reportes del sistema; no hay separación de datos.
- No se puede registrar usuarios desde la UI ni la API; el formulario de sign-up de la plantilla es solo visual (valida y no envía nada).
- El login valida `username`/`password` y devuelve token + datos básicos del usuario; no hay noción de empresa ni de rol en la sesión del frontend ni en las respuestas.
- Las respuestas de la API no contienen datos de empresa.

### Restricciones
- `CLAUDE.md`: "Cambios acotados a un objetivo; antes de tocar varios archivos, proponer un plan y esperar confirmación" — este task toca prácticamente todos los módulos.
- `CLAUDE.md`: "Nunca editar una migración ya aplicada: crear una nueva con `makemigrations`" — el campo de empresa en las cinco tablas de negocio requiere migraciones nuevas, y la columna obligatoria sobre tablas con datos exige una estrategia de datos existentes.
- `CLAUDE.md`: "Avisar antes de instalar cualquier dependencia nueva" (relevante si se evalúa una librería de multi-tenancy).
- `CLAUDE.md` y `ddd.md`: "los módulos no se importan infraestructura entre sí", el dominio no importa Django, comunicación entre módulos solo por `services.py` (verificado por `test_boundaries.py`). Cualquier contexto de empresa que viaje entre módulos debe respetarlo.
- `ddd.md:1253` y `CLAUDE.md`: "Multiempresa compleja" está fuera del MVP — el requerimiento actual es una forma simple (una empresa por usuario, aislamiento por columna); la frontera entre "simple" y "compleja" es una decisión pendiente.
- `CLAUDE.md` frontend: Reactive Forms, tipos explícitos sin `any`, lógica no visual en services, sin suscripciones colgadas; el formulario actual usa `UntypedFormBuilder`.
- `CLAUDE.md`: no leer ni modificar `.env`/secretos.

### Riesgos identificados
- **Fuga entre empresas** si algún camino de lectura/escritura omite el filtro: hay al menos cuatro rutas distintas (repositorios, `read_queries` de reportes, `expenses/services.py` con `ExpenseModel.objects` directo, y fachadas por id usadas en validaciones cruzadas de Sales). Un solo olvido expone datos de otra empresa.
- **Acceso por id (IDOR)**: los detalles se obtienen por UUID (`get(product_id)`, `get(order_id)`); sin filtro de empresa un usuario con un UUID ajeno accedería a datos ajenos.
- **Unicidad global**: `expenses_category_name_ci_unique` (`expenses/.../models.py:19-21`) y la detección de teléfono duplicado (`customers/.../repositories.py:55-59`) son globales y chocarían con varias empresas.
- **Migración sobre datos existentes**: columna obligatoria de empresa en tablas ya pobladas; riesgo de pérdida o mala asignación. Reversibilidad no evaluada.
- **Cambio de contrato de API** que rompe los 7 servicios del frontend y sus specs si se agrega empresa a rutas/payloads; si va solo en el token/contexto, el impacto es menor (decisión de arquitectura).
- **Registro público**: endpoint sin autenticación, riesgo de abuso/enumeración de empresas; ya existe throttle para login pero no para registro.
- **Seguridad de autorización**: cambio de modelo de autenticación/autorización sin tests previos de permisos (no existen); cubierto por la regla `NEEDS_ARCHITECTURE`.
- **Divergencia del formulario**: la plantilla pide email y no username; el login actual usa username (posible desajuste de identidad).
- **Arquitectura**: `accounts` no está en la documentación DDD y la regla "Multiempresa compleja fuera del MVP" puede requerir actualizar `ddd.md` o registrar una excepción.
- **Cobertura de tests**: cambios de firma en repositorios/fachadas/puertos afectan `fakes.py` y tests de cinco módulos.

### Preguntas abiertas (para PLAN/ARCHITECT; no se resuelven aquí)
1. ¿Registrarse con un nombre de empresa **crea** una empresa nueva, o **se une** a una existente? ¿Qué pasa si el nombre ya existe (¿mayúsculas/acentos?)?
2. ¿El primer usuario que crea la empresa es admin automáticamente? ¿Quién crea a los siguientes usuarios de la empresa y cómo (¿el mismo sign-up o una pantalla admin)?
3. ¿El registro es público (anónimo) o restringido?
4. ¿El login sigue siendo por `username` o pasa a `email`? ¿El sign-up pedirá `username`?
5. ¿"Incluir el nombre de empresa en las llamadas API" significa que el cliente lo envía explícitamente (header/ruta/query) o que se deriva de la sesión? Si el cliente lo envía, ¿cómo se valida contra la empresa del usuario?
6. ¿Qué hacer con los datos que ya existen (asignar a una empresa por defecto, borrar)?
7. ¿Un usuario puede pertenecer a más de una empresa en el futuro?

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — Cumple varios indicadores: cambios de autenticación/autorización (registro, roles), cambios importantes de base de datos (propietario de datos en cinco módulos, restricciones de unicidad, migración de datos), impacto en múltiples módulos y en el contrato de API, y toca una capacidad que la documentación lista como fuera del MVP ("Multiempresa compleja"), con riesgo de deuda técnica alto si el aislamiento se hace de forma dispersa.

### Diseño requerido
**SI** — Hay una pantalla existente de la plantilla (sign-up) que se adapta con un campo nuevo, textos y un flujo post-registro (¿redirige a login, entra directo al dashboard?), y puede requerir mostrar empresa/rol en la UI o una pantalla de gestión de usuarios para el admin; conviene decidir el flujo y la consistencia visual antes de implementar. (Ante la duda, SI.)

## Diseño
- [DDR-registro-usuarios-empresa-multitenant-pantalla-registro](../design/DDR-registro-usuarios-empresa-multitenant-pantalla-registro.md) — registro con nombre de empresa (tarjeta única como el login), entrada directa al dashboard, empresa y usuario en el menú del header. Pendiente de arquitectura: crear vs. unirse a empresa, username vs. correo, y si el registro devuelve sesión.

## Arquitectura

**Decisión de negocio (usuario, 2026-10-12):** el registro público solo crea empresas nuevas; un nombre de empresa existente se rechaza; los usuarios adicionales de una empresa los agrega su admin (por ahora vía Django admin; sin pantalla en esta tarea).

- [ADR-registro-usuarios-empresa-multitenant-modelo-aislamiento](../adr/ADR-registro-usuarios-empresa-multitenant-modelo-aislamiento.md) — un esquema, columna `company_id` UUID en las tablas raíz (sin FK entre módulos), empresa por defecto para datos existentes, unicidades por empresa, migraciones reversibles.
- [ADR-registro-usuarios-empresa-multitenant-propagacion-contexto-empresa](../adr/ADR-registro-usuarios-empresa-multitenant-propagacion-contexto-empresa.md) — la empresa sale siempre del token (no se envía en las llamadas; se devuelve en login/registro); repositorios con `company_id` obligatorio en el constructor, fachadas y adaptadores con empresa; 404 sobre ids ajenos; pruebas de fuga.
- [ADR-registro-usuarios-empresa-multitenant-registro-roles](../adr/ADR-registro-usuarios-empresa-multitenant-registro-roles.md) — `Company` y `User.role` en `accounts`, `POST /api/auth/register/` público con throttle e interruptor `REGISTRATION_ENABLED`, permiso por defecto `CompanyAdminPermission`.

**Desviación consciente del requerimiento:** "incluir el nombre de empresa en las llamadas API" se cumple del lado servidor (filtrado por la empresa de la sesión) y no con un parámetro enviado por el cliente, que no aportaría seguridad.

**Para PLAN:** actualizar `docs/architecture/ddd.md` (multiempresa simple, `accounts`/`Company`), `CLAUDE.md` y `.env.example` (`REGISTRATION_ENABLED`); ajustar `fakes.py` y tests de los 5 módulos; agregar `accounts/admin.py`.

## Plan
- [PLAN-2026-10-12-registro-usuarios-empresa-multitenant](../plans/PLAN-2026-10-12-registro-usuarios-empresa-multitenant.md) — **v1**, Modo COMPLETO, Specification **READY**. 16 AC; fases A (identidad/permiso), B (aislamiento por módulo), C (guardas y migración), D (frontend), E (docs y verificación). E2E: NO. Sin dependencias nuevas.

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
