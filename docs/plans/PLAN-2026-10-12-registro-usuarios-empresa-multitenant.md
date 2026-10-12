# PLAN-2026-10-12-registro-usuarios-empresa-multitenant (v1)

**Task:** TASK-registro-usuarios-empresa-multitenant
**Modo:** COMPLETO
**DDRs relacionados:** [DDR-registro-usuarios-empresa-multitenant-pantalla-registro](../design/DDR-registro-usuarios-empresa-multitenant-pantalla-registro.md)
**ADRs relacionados:** [modelo-aislamiento](../adr/ADR-registro-usuarios-empresa-multitenant-modelo-aislamiento.md), [propagacion-contexto-empresa](../adr/ADR-registro-usuarios-empresa-multitenant-propagacion-contexto-empresa.md), [registro-roles](../adr/ADR-registro-usuarios-empresa-multitenant-registro-roles.md)
**Specification readiness:** READY

**Por qué COMPLETO:** los tres ejes están activos — comportamiento de dominio/seguridad (aislamiento por empresa, rol), frontera cruzada (los 5 módulos y sus fachadas) y contrato/datos con costo de reversa (migraciones con relleno, permiso por defecto, endpoint nuevo, ADR).

## Objective
Permitir que una persona se registre desde el formulario de sign-up de la plantilla indicando el nombre de su empresa (obligatorio), y que a partir de ahí **cada usuario vea y modifique únicamente los datos de su empresa** en todo el sistema (catálogo, clientes, pedidos y pagos, gastos y reportes), con un rol `admin` que tiene acceso total a los datos de su empresa.

## Context
Ver `docs/tasks/TASK-registro-usuarios-empresa-multitenant.md` (investigación, DDR y ADR). Verificado contra `origin/main` (`3f23533`): las rutas y firmas citadas en la investigación siguen vigentes. Decisión de negocio del usuario: el registro público solo crea empresas nuevas; un nombre existente se rechaza; los usuarios adicionales los agrega el admin (por ahora vía Django admin).

# Specification

## Domain context
**Bounded Context:** `accounts` (identidad; infraestructura, no contexto de negocio) para empresa, usuario y rol; **aislamiento transversal** sobre `catalog`, `customers`, `sales`, `expenses` y `reporting`.
**Related contexts:** `sales → {catalog, customers}` y `reporting → {sales, expenses, customers}` (mapa vigente en `sales/tests/test_boundaries.py`; no cambia).

## Ubiquitous language
| Term | Meaning | Source |
|---|---|---|
| Empresa (`Company`) | Unidad propietaria de los datos de negocio; un usuario pertenece a una sola | TASK, ADR registro-roles |
| Nombre de empresa | Texto que identifica a la empresa; único sin distinguir mayúsculas ni espacios sobrantes | ADR registro-roles |
| Admin | Rol con acceso total a los datos de su empresa; único rol hoy | TASK (requerimiento), ADR registro-roles |
| Registro | Alta pública: crea empresa + primer usuario admin y deja la sesión iniciada | DDR, ADR registro-roles |
| Empresa por defecto | Empresa con UUID fijo que recibe los datos y usuarios existentes al migrar | ADR modelo-aislamiento |
| `username` / "Usuario" | Identificador de login; el formulario lo llama "Usuario" | `auth.service.ts:29-31`, DDR |

Inconsistencias declaradas: la plantilla pide *email* y no *usuario* (`signup.component.ts:25-30`) mientras el login usa `username`; se resuelve con el campo "Usuario" (DDR/ADR), `email` se guarda sin unicidad. El requerimiento dice "incluir el nombre de empresa en las llamadas API"; se cumple del lado servidor (ADR propagación), no con un parámetro del cliente.

## Current behavior
- Todos los datos de negocio son globales (modelos sin propietario: `catalog/infrastructure/django/models.py:6-17`, `customers/.../models.py:6-19`, `sales/.../models.py:7-71`, `expenses/.../models.py:8-44`); repositorios y consultas de reporte leen `Model.objects` completo (`catalog/.../repositories.py:33-47`, `sales/.../read_queries.py:16-82`, `expenses/services.py:34-51`).
- Solo existen login y logout (`accounts/api/urls.py:5-8`); `User` está vacío (`accounts/models.py:4-6`); permiso por defecto `IsAuthenticated` (`config/settings/base.py:83-85`).
- El sign-up de la plantilla no envía nada (`signup.component.ts:38-48`).

## Expected behavior
1. Una persona anónima se registra con empresa, nombre, apellido, usuario, correo y contraseña; se crea la empresa y su usuario admin, y queda con sesión iniciada (token) en el dashboard.
2. Toda petición a la API de negocio opera sobre la empresa del usuario autenticado, derivada del token; el cliente no puede elegir ni cambiar la empresa.
3. Recursos de otra empresa no existen para el usuario (404); crear/modificar siempre ocurre dentro de su empresa.
4. Los reportes calculan solo con datos de la empresa del usuario.
5. Los datos y usuarios existentes antes del cambio pasan a la empresa por defecto sin pérdida.

## Domain rules / invariants
**Existentes (deben seguir verdaderas):** todas las reglas de dominio de `catalog`, `customers`, `sales`, `expenses` y `reporting` (no se tocan); Reporting solo lee; los módulos de negocio no se importan infraestructura entre sí ni importan `accounts`; dinero en `Decimal`.
**Nuevas:**
- INV-01: toda fila de las tablas raíz de negocio (`catalog_product`, `customers_customer`, `sales_order`, `expenses_category`, `expenses_expense`) pertenece a exactamente una empresa (`company_id` obligatorio).
- INV-02: la empresa activa de una petición se deriva del usuario autenticado en el servidor; nunca de la ruta, query, header ni cuerpo.
- INV-03: el nombre de empresa es único sin distinguir mayúsculas ni espacios sobrantes (restricción de BD).
- INV-04: las entidades de dominio no conocen la empresa.
- INV-05: un usuario pertenece a lo sumo a una empresa y las empresas no se borran (se desactivan).
- INV-06: dentro de una empresa se mantienen las unicidades actuales (categoría de gasto por nombre sin distinguir mayúsculas; teléfono de cliente como advertencia confirmable); **entre** empresas no hay colisión.

## Acceptance criteria
- AC-01: **Registro.** Given datos válidos, When `POST /api/auth/register/`, Then `201` con `{token, user:{id, username, first_name, last_name, role:'admin', company:{id, name}}}`; existe una empresa nueva y el usuario es su admin; el token autentica llamadas posteriores a la API de negocio.
- AC-02: **Nombre de empresa existente.** Given una empresa "Cuñapés SRL", When se registra otra con " cuñapés srl " (distinto caso/espacios), Then `400` con error en `company_name`, y no se crea empresa ni usuario (atomicidad).
- AC-03: **Validación.** `username` repetido → `400` en `username`; contraseña rechazada por los validadores de Django → `400` en `password`; campos obligatorios vacíos (`company_name`, `username`, `first_name`, `last_name`, `email`, `password`) → `400` por campo; nunca se devuelve la contraseña ni su hash.
- AC-04: **Aislamiento de lectura.** Given dos empresas A y B con datos, When un usuario de A lista/consulta productos, clientes, pedidos (y sus pagos), gastos y categorías, Then solo ve los de A; los detalles/acciones sobre ids de B responden `404` igual que un id inexistente (GET, PATCH y acciones de estado).
- AC-05: **Aislamiento de escritura.** Lo que crea un usuario de A queda en A; un `company`/`company_id` en el cuerpo se ignora; ninguna acción (editar, activar/desactivar, cancelar, entregar, registrar pago, anular gasto) afecta filas de B.
- AC-06: **Referencias cruzadas.** Un pedido de A que referencia `product_id` o `customer_id` de B se trata como inexistente (mismo error que hoy ante un id desconocido); un gasto con `category_id` de B igual.
- AC-07: **Unicidad por empresa.** Dos empresas pueden tener una categoría "Empaque" y clientes con el mismo teléfono sin advertencia ni conflicto; dentro de una misma empresa se conserva el comportamiento actual.
- AC-08: **Reportes.** Dashboard, ventas, gastos, por canal, top productos, top clientes y pendientes de A no incluyen importes ni filas de B; los nombres de cliente se resuelven solo dentro de A.
- AC-09: **Permiso por defecto.** Un usuario sin empresa, con empresa inactiva o con rol distinto de `admin` recibe `403` en toda la API de negocio; los endpoints públicos (`login`, `register`, `health`) siguen accesibles y `logout` solo requiere autenticación.
- AC-10: **Login.** `POST /api/auth/login/` conserva su contrato y agrega `role` y `company {id, name}` al `user` (usuario sin empresa: `company: null`); un usuario o empresa inactivos reciben el `401` genérico actual.
- AC-11: **Abuso.** El registro tiene throttle propio (scope `register`, `5/hour`, devuelve `429`); con `REGISTRATION_ENABLED=False` el endpoint responde `403` y no crea nada.
- AC-12: **Migración.** Sobre una base con datos previos, tras `migrate` todos los usuarios y filas de negocio apuntan a la empresa por defecto (UUID fijo), ninguna fila queda sin `company_id`, los conteos no cambian y cada migración es reversible (`migrate` hacia atrás).
- AC-13: **Contrato sin regresión.** Las rutas, parámetros y formas de respuesta de los endpoints de negocio no cambian (solo se agregan campos en login/registro).
- AC-14: **UI de registro** (DDR): tarjeta única con el logo de login, campos Empresa/Nombre/Apellido/Usuario/Correo/Contraseña/Confirmar contraseña, sin social ni términos; valida en el cliente (obligatorios, correo, contraseñas iguales); errores `400` por campo bajo el control; `403/429/red` en alerta general; éxito → `/dashboard/main` con sesión.
- AC-15: **Header.** El menú de usuario muestra nombre y apellido (o usuario) y el nombre de la empresa de la sesión, en lugar del saludo fijo.
- AC-16: **Guardas.** Existen pruebas automáticas que fallan si (a) una tabla raíz de negocio no tiene `company_id`, (b) un módulo de negocio importa `modules.accounts`, o (c) un endpoint de negocio devuelve datos de otra empresa.

## Edge cases
- EDGE-01: carrera entre dos registros con el mismo nombre de empresa o usuario → una sola alta; la otra recibe `400` por la restricción de BD (sin `500`).
- EDGE-02: superusuario creado con `createsuperuser` (sin empresa): accede a Django admin; en la API de negocio recibe `403`.
- EDGE-03: sesión guardada en el navegador antes del cambio (sin `company`/`role` en `localStorage`): sigue autenticada; el header muestra solo el usuario hasta el próximo login.
- EDGE-04: `GET` de un id de B con formato UUID válido, inexistente o mal formado → la misma respuesta que hoy (404/validación), sin distinguir "existe en otra empresa".
- EDGE-05: base vacía: la migración crea la empresa por defecto sin filas dependientes; el primer registro funciona.
- EDGE-06: nombre de empresa con solo espacios o más de 150 caracteres → `400` en `company_name`.

## Error cases
- `400` por campo (registro); `401` genérico (login); `403` (sin empresa/rol/empresa inactiva, registro deshabilitado); `404` (recurso fuera de la empresa); `429` (throttle). El formato de error de negocio existente no cambia.

## Authorization / permissions
- Anónimo: solo `login`, `register`, `health`.
- Autenticado con empresa activa y rol `admin`: toda la API de negocio **de su empresa** (ver, crear, modificar).
- Cualquier otro: `403`. La verificación ocurre en el servidor (permiso por defecto DRF `CompanyAdminPermission`); el frontend no es barrera.
- Alta de usuarios adicionales: solo Django admin (staff de plataforma), fuera de la API.

## API contract
- API-01: `POST /api/auth/register/` — público, sin `Authorization`. Request: `{company_name, username, first_name, last_name, email, password}`. `201`: `{token, user:{id, username, first_name, last_name, role, company:{id, name}}}`. Errores: `400` `{<campo>: [mensajes]}`; `403` `{detail}` si el registro está deshabilitado; `429` por throttle.
- API-02: `POST /api/auth/login/` — igual que hoy; `user` agrega `role` y `company` (aditivo).
- API-03: resto de endpoints sin cambios de ruta, parámetros ni forma; nuevo `404` para ids de otra empresa (mismo mensaje que "no encontrado").
- Compatibilidad: clientes actuales que ignoran campos nuevos siguen funcionando.

## UI behavior
Derivado del DDR (no se rediseña):
- UI-01: registro en tarjeta única (`.login-card--single`), logo `main-logo.png`, textos en español, botón "Crear cuenta" habilitado salvo durante el envío.
- UI-02: estados: inicial · enviando · error de campo · error general · éxito.
- UI-03: éxito → sesión guardada como en el login y navegación a `DEFAULT_ROUTE_AFTER_LOGIN`.
- UI-04: header: título del dropdown con nombre y apellido (fallback usuario) y línea atenuada con la empresa.
- UI-05: el enlace "Sign Up" del login ya existe (`signin.component.html`); se agrega el texto "¿Ya tienes cuenta? Inicia sesión" en el registro.

## Non-functional requirements
- Seguridad: aislamiento verificado por pruebas; registro con throttle e interruptor; mensajes sin revelar existencia de recursos de otra empresa.
- Rendimiento: `company_id` indexado; sin consultas N+1 nuevas (los filtros se aplican en la misma consulta).
- Compatibilidad hacia atrás: contrato de negocio intacto; migraciones reversibles.

## Out of scope
- Pantalla o endpoint para que el admin cree/gestione usuarios, aprobación de miembros, múltiples empresas por usuario, roles adicionales, edición/renombre de empresa, recuperación de contraseña, verificación de correo, login por correo, expiración de tokens, RLS en PostgreSQL, limpieza de login (social/inglés) y redirección de usuarios ya autenticados fuera de `/signup`.

## Open questions
(No bloquean la implementación; se asume lo indicado.)
- Q1: `email` se guarda sin unicidad (no hay requisito); se asume así.
- Q2: largo máximo de `company_name` = 150 (igual que otros nombres del sistema); se asume.
- Q3: ¿un superusuario sin empresa debería poder iniciar sesión por API? Se asume que sí obtiene token pero la API de negocio responde `403` (ADR); revisable.

# Test Specification

## Unit tests
- `accounts`: modelo `Company` (nombre normalizado y único sin distinguir caso/espacios), `User.role` por defecto, función de registro (atómica; rollback si falla el usuario), `CompanyAdminPermission` (matriz: sin empresa, empresa inactiva, rol distinto, ok), `shared/tenancy.py`.
- Dominio de cada módulo: **sin cambios** (INV-04); no se agregan tests de dominio.
- Frontend: `AuthService.register` (mapeo de respuesta y errores), `SignupComponent` (campos, validadores, contraseñas distintas, errores por campo, alerta general, navegación), header (nombre/empresa).

## Integration tests
- Backend (`APITestCase`, PostgreSQL real): registro (AC-01..03, AC-11, EDGE-01/06), login (AC-10), permiso por defecto (AC-09, EDGE-02), aislamiento y fuga por endpoint de los 5 recursos y reportes con dos empresas (AC-04..08, AC-13), repositorios con `company_id` (consulta, `get_for_update`, `save`).
- Migraciones: prueba que aplica el estado anterior con datos, migra y verifica relleno y reversa (AC-12), usando `MigrationExecutor`.
- Guardas (AC-16): prueba de introspección de modelos y ampliación de `sales/tests/test_boundaries.py`.

## E2E
**¿Corresponde E2E?** NO. `playwright`/`cypress` no están en `frontend/panel_admin/package.json`; instalarlo es una dependencia nueva que no se justifica aquí: el contrato frontend↔backend lo cubren los tests de API (backend) y `HttpTestingController` (Angular), y el flujo es un único formulario sin pasos múltiples. Recomendación (no bloqueante): validar a mano registro → dashboard → ver solo datos propios con dos empresas, usando `/run`.

## Regression tests
- Se reutilizan los ~4.600 líneas de tests existentes de `catalog`, `customers`, `sales`, `expenses`, `reporting` y `accounts`: deben pasar tras adaptarse a autenticar con un usuario de empresa (helper común) y a los constructores nuevos de repositorios/adaptadores, **sin cambiar sus expectativas de comportamiento**.
- Frontend: specs existentes (`orders-api.service.spec.ts`, `interceptors.spec.ts`, `auth.service.spec.ts`, `auth.guard.spec.ts`) siguen verdes; `npm run lint` y `npm run build` sin errores.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | Backend integration (`accounts`) |
| AC-02 | Backend integration (incl. atomicidad) |
| AC-03 | Backend integration |
| AC-04 | Backend integration por recurso (dos empresas) |
| AC-05 | Backend integration (escritura y acciones) |
| AC-06 | Backend integration (Sales, Expenses) |
| AC-07 | Backend integration (Expenses, Customers) |
| AC-08 | Backend integration (Reporting) + unit de fachadas |
| AC-09 | Backend unit (permiso) + integration |
| AC-10 | Backend integration |
| AC-11 | Backend integration (throttle con `cache.clear()`, interruptor con `override_settings`) |
| AC-12 | Backend migration test |
| AC-13 | Regresión: suites existentes sin cambios de expectativa |
| AC-14 | Angular unit (`SignupComponent`, `AuthService`) |
| AC-15 | Angular unit (header) |
| AC-16 | Backend test de introspección + boundaries |

# Implementation Plan

## Architecture considerations
- Respeta los 3 ADR: columna `company_id` sin FK entre módulos; empresa derivada del token; repositorios con empresa en el constructor; fachadas con `company_id` como primer argumento; adaptadores construidos con `company_id` (puertos de aplicación y casos de uso **no cambian de firma**).
- `docs/architecture/ddd.md`: dominio sin Django y sin empresa; módulos sin importar `accounts` (nuevo test); Reporting solo lectura.
- Dinero en `Decimal`: no se toca ningún cálculo.
- Seguridad: cambio de `DEFAULT_PERMISSION_CLASSES` es el punto sensible; ver Risks.

## Proposed solution
1. `accounts`: `Company`, `User.company` (nullable, `PROTECT`), `User.role`; registro con función de aplicación; permiso por defecto; throttle e interruptor; admin de Django.
2. `shared/tenancy.py`: helper para leer `request.user.company_id` (error explícito si falta).
3. Por módulo de negocio: `company_id` en el modelo + migración con relleno; repositorios/fachadas/adaptadores/read_queries con empresa; views construyen todo con `company_id` del helper.
4. Frontend: `AuthService.register`, `User` con rol/empresa, `SignupComponent` según DDR, header.
5. Pruebas y guardas; documentación.

## Files/components affected
- **Backend `accounts`:** `models.py`, `migrations/0002_*.py`, `api/{serializers,views,urls,permissions}.py`, `registration.py` (nuevo), `admin.py` (nuevo), `testing.py` (helpers de test), `tests.py`.
- **Backend `shared`:** `tenancy.py` (nuevo) + `tests/test_tenancy.py`.
- **Backend `config`:** `settings/base.py` (permiso por defecto, scope `register`, `REGISTRATION_ENABLED`), `.env.example`.
- **catalog:** `infrastructure/django/{models,repositories}.py`, `services.py`, `api/views.py`, `migrations/0002_*`, tests.
- **customers:** `infrastructure/django/{models,repositories}.py`, `services.py`, `api/views.py`, `migrations/0002_*`, tests.
- **expenses:** `infrastructure/django/{models,repositories}.py` (incl. restricción por empresa), `services.py`, `api/views.py`, `migrations/0002_*`, tests.
- **sales:** `infrastructure/django/{models,repositories,read_queries}.py`, `infrastructure/adapters.py`, `services.py`, `api/views.py`, `migrations/0002_*`, `tests/{fakes,test_*,test_boundaries}.py`.
- **reporting:** `infrastructure/adapters.py`, `api/views.py`, tests.
- **Frontend:** `core/models/user.ts`, `core/service/auth.service.ts` (+spec), `authentication/signup/signup.component.{ts,html,scss/sass,spec.ts}`, `layout/header/header.component.{ts,html}` (+spec).
- **Documentación:** `docs/architecture/ddd.md`, `CLAUDE.md`, `.env.example`.

## Implementation steps
Fase A — Identidad y permiso (base de todo)
1. `accounts`: `Company` (UUID, `name`, `is_active`, `created_at`, restricción `Lower(name)`), `User.company` (FK `PROTECT`, nullable) y `User.role` (`TextChoices` con `admin`, default `admin`). Migración `0002`: esquema + `RunPython` que crea la empresa por defecto con UUID literal `00000000-0000-4000-8000-000000000001` y asigna `company` a **todos** los usuarios existentes; reversa vacía. (INV-03, INV-05, AC-12)
2. `accounts/api/permissions.py`: `CompanyAdminPermission`; en `base.py` pasa a `DEFAULT_PERMISSION_CLASSES`; `health` y login/registro mantienen `AllowAny` explícito. (AC-09)
3. `shared/tenancy.py`: `company_id_from(request)`; error explícito si el usuario no tiene empresa. (INV-02)
4. `accounts/registration.py` + `RegisterSerializer` + `RegisterView` (`/api/auth/register/`): transacción única (empresa → usuario con `validate_password` → token); normaliza espacios del nombre; captura `IntegrityError` → `400` por campo; throttle `register` `5/hour`; `REGISTRATION_ENABLED` (`env.bool`, default `True`) → `403` si falso. (AC-01..03, AC-11, EDGE-01/06)
5. `UserSerializer`: agrega `role` y `company {id, name}`/`null`; login rechaza usuario o empresa inactivos con el `401` genérico. (AC-10)
6. `accounts/admin.py`: `Company` y `User` con `company` y `role` editables (alta de usuarios adicionales). `accounts/testing.py`: `make_company`, `make_admin`, `authenticated_client`.

Fase B — Aislamiento por módulo (repetir por módulo, en este orden: catalog → customers → expenses → sales → reporting)
7. **Modelo + migración `0002`:** agregar `company_id = UUIDField(db_index=True)`; migración: nullable → `RunPython` asigna el UUID por defecto → `NOT NULL`; en `expenses`: reemplazar `expenses_category_name_ci_unique` por `UniqueConstraint('company_id', Lower('name'))`. (INV-01, INV-06, AC-12)
8. **Repositorios:** constructor recibe `company_id`; `get`, `get_for_update`, `list`, `find_by_phone`, `find_by_name`, `get_many`, agregados (`total_active`) y consultas internas filtran por empresa; `save` fija `company_id` al crear (y no lo cambia al actualizar). Mappers/entidades sin cambios. (INV-01, INV-04, AC-04, AC-05, AC-07)
9. **Fachadas** (`catalog/customers/sales/expenses services.py`): `company_id` como primer argumento y filtro en cada consulta; `read_queries.py` parte de un queryset filtrado. (AC-06, AC-08)
10. **Adaptadores** (`sales/infrastructure/adapters.py`, `reporting/infrastructure/adapters.py`): constructor con `company_id` que pasan a las fachadas; puertos y casos de uso intactos. (AC-06, AC-08)
11. **Views:** obtener `company_id` con el helper y construir repositorios/adaptadores con él; `_repository()`-style factories por request. Sin cambios de ruta ni de respuesta. (AC-13)
12. **Tests del módulo:** autenticar con helper de `accounts/testing.py`; adaptar `fakes.py` y `test_repository.py`; agregar casos con dos empresas (lectura, escritura, 404 ajeno, unicidad). (AC-04..08)

Fase C — Guardas y migración
13. Prueba de introspección: toda tabla raíz de negocio tiene `company_id` (lista explícita de hijas `sales_order_item`, `sales_payment`). Ampliar `test_boundaries.py`: ningún módulo de negocio importa `modules.accounts` (excluyendo tests). (AC-16)
14. Prueba de migración (`MigrationExecutor`): estado previo con datos → migrar → relleno y conteos → reversa. (AC-12)

Fase D — Frontend
15. `core/models/user.ts` y `LoginResponse`: `role` y `company`; `AuthService.login` los mapea; guardar en `LocalStorageService` como hoy. (AC-10, EDGE-03)
16. `AuthService.register(input)`: `POST /auth/register/`, mismo mapeo/persistencia que `login`; errores tipados: campos (`400`), `403` deshabilitado, `429`, red. Spec con `HttpTestingController`. (AC-14)
17. `SignupComponent` según DDR: `NonNullableFormBuilder`, validadores (obligatorios, correo, coincidencia), `serverErrors` por campo, alerta general, `loading`, navegación a `DEFAULT_ROUTE_AFTER_LOGIN`; HTML con `.login-card--single`; se eliminan social y términos y la imagen lateral. Spec completo. (AC-14, UI-01..03, UI-05)
18. Header: `dropdown-title` con nombre/empresa desde `AuthService.currentUser`. Spec. (AC-15, UI-04)

Fase E — Documentación y verificación
19. `ddd.md` (multiempresa simple, `accounts`/`Company`/rol), `CLAUDE.md` (variable `REGISTRATION_ENABLED`, regla "toda consulta de negocio filtra por empresa; repositorios exigen `company_id`") y `.env.example`.
20. Verificar: `python manage.py test` completo, `makemigrations --check`, `bandit` (dev.txt), `npm test`, `npm run lint`, `npm run build`; revisión manual con dos empresas (`/run`).

## Database / migrations
- `accounts/0002`, `catalog/0002`, `customers/0002`, `expenses/0002`, `sales/0002`: nuevas, sin tocar `0001`. Orden: `accounts` primero (empresa por defecto); las apps de negocio no dependen de `accounts` (UUID literal copiado en cada migración).
- Relleno en la misma migración que impone `NOT NULL` (no hay estado mixto en despliegue).
- Rollback: reversible por esquema; asignaciones a empresa se pierden, datos de negocio no. La reversa de la restricción de `expenses` puede fallar si ya hay categorías con el mismo nombre en distintas empresas (runbook: renombrar/fusionar antes). Respaldar (`pg_dump`) antes de aplicar en un entorno con datos.

## Risks
- **Olvido de un filtro** (fuga entre empresas): mitigado con repositorios que exigen `company_id`, pruebas de fuga por endpoint y de introspección (AC-16). No elimina el riesgo en repositorios futuros.
- **Permiso por defecto:** un usuario existente sin empresa pierde acceso; mitigado porque `0002` asigna la empresa por defecto a todos. `createsuperuser` nuevo queda sin empresa (EDGE-02) → documentar en `CLAUDE.md` y asignar vía Django admin.
- **Volumen de tests a adaptar** (~4.600 líneas): cambio mecánico (helper de autenticación + constructores); riesgo de enmascarar regresiones si se alteran expectativas → regla: no cambiar expectativas, solo la preparación.
- **Enumeración** de nombres de empresa y usuarios por el registro público: aceptado y limitado por throttle e interruptor.
- **Datos reales previos al cambio:** si existen en algún entorno compartido, quedarán en la empresa por defecto; renombrarla en Django admin.
- **Sesiones antiguas** en el navegador sin `company`/`role` (EDGE-03): solo afecta el header hasta el próximo login.
- **Unicidad global de `username`:** sigue siendo global (Django); dos empresas no pueden tener el mismo usuario. Aceptado (fuera de alcance).

## New dependencies
Ninguna.

## Changelog
_(v1: documento inicial.)_
