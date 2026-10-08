# PLAN-2026-10-08-clientes-mvp (v1)

**Task:** TASK-clientes-mvp
**Modo:** COMPLETO
**DDRs relacionados:** [DDR-clientes-mvp-menu-y-pantallas-cliente](../design/DDR-clientes-mvp-menu-y-pantallas-cliente.md)
**ADRs relacionados:** [modelo-dominio](../adr/ADR-clientes-mvp-modelo-dominio.md), [contrato-api](../adr/ADR-clientes-mvp-contrato-api.md), [historial-compras](../adr/ADR-clientes-mvp-historial-compras.md), [frontend-feature](../adr/ADR-clientes-mvp-frontend-feature.md)
**Specification readiness:** READY

> Modo COMPLETO por el eje 1 (reglas de dominio nuevas: normalización de teléfono y detección de duplicados), el eje 2 (dependencia con Sales: el historial y la asociación a pedido cruzan contextos) y el eje 3 (contrato API nuevo, migración nueva, cuatro ADR y un DDR con impacto visual).

## Objective
Implementar el módulo Cliente (REQ-CUS-001, 002, 003, 005, 006 completos en backend y UI; REQ-CUS-004 a nivel de interfaz y contrato): API REST en `backend/modules/customers`, pantallas Angular de lista, alta/edición y perfil, y la entrada de menú "Cliente". El historial real y la asociación del cliente a un pedido se cierran con el task de Sales (que aún no existe).

## Context
Ver `docs/tasks/TASK-clientes-mvp.md`. Verificado hoy sobre `main` (`d85f16e`): `backend/modules/` tiene `accounts` y `catalog`; `backend/config/urls.py:6-11` monta `admin/`, `api/health/`, `api/auth/` y `api/products/`; `backend/config/settings/base.py:11-22` registra `modules.accounts` y `modules.catalog`; no hay `customers` ni `sales`; `backend/requirements/base.txt` no tiene librería de teléfonos; `frontend/panel_admin/src/app/features/` solo tiene `products/`; `routes.json` tiene Dashboard y Catálogo; no hay Playwright en `frontend/panel_admin/package.json`. Todo coincide con la investigación. El patrón a seguir es el de `catalog`/`features/products` (ya implementado y publicado).

# Specification

## Domain context
**Bounded Context:** Customers. **Related contexts:** Sales (futuro, no existe) referenciará `customer_id` y proveerá el historial; Reporting (futuro) solo lee. Ninguno se toca ni se importa (`ddd.md:753-779`).

## Ubiquitous language
| Term | Meaning | Source |
|---|---|---|
| Cliente (`Customer`) | Persona o entidad que compra; identificada por un UUID estable | REQ-CUS, `ddd.md:240` |
| Perfil / detalle | La pantalla de un cliente (`customer-detail`) | REQ-CUS-002/004, `ddd.md:1055` |
| `active` / activo, inactivo ("desactivar") | Si el cliente aparece por defecto entre los clientes activos; no implica borrado | REQ-CUS-005 |
| Teléfono normalizado | `+` + código de país + dígitos, cuando el número cumple las reglas de normalización; si no, el texto recortado tal cual | REQ-CUS-001/006, ADR modelo-dominio |
| Duplicado evidente | Otro cliente (activo o inactivo) con el mismo `phone` almacenado | REQ-CUS-006 |
| Historial de compras | Pedidos del cliente (fecha, total, estado) provistos por Sales | REQ-CUS-004, ADR historial-compras |

Inconsistencias declaradas: (1) el requisito dice "perfil", el DDD y el código dirán `customer-detail`/detalle; (2) el requisito dice "historial de compras", habla de "pedidos" y el DDD lo llama `GetCustomerPurchaseHistory` (Customers) y `ListOrdersByCustomer` (Sales): este plan lo trata como contrato de Sales, no de Customers (ADR); (3) el requisito solo menciona "desactivar", pero la API también incluye `activate` (por simetría y por el patrón de `catalog`; `ddd.md:930-937` no lo lista); (4) nombres en español en UI/REQ y en inglés en API/dominio (convención del proyecto).

## Current behavior
No hay clientes: `GET /api/customers/` → 404 (`backend/config/urls.py:6-11`). El menú muestra Dashboard y Catálogo (`routes.json`). No hay pantallas de clientes ni de pedidos.

## Expected behavior
Un usuario autenticado puede, por API y por pantallas, crear un cliente (solo el nombre es obligatorio), editar sus datos, buscarlo por nombre o teléfono, consultarlo, y activarlo/desactivarlo; nunca se borra. El teléfono se guarda normalizado cuando es posible. Al crear un cliente con un teléfono ya registrado, el sistema avisa y solo crea si el usuario confirma. El perfil incluye la sección "Historial de compras" con su estado vacío (sin consultar Sales). El menú lateral tiene la entrada "Cliente" además de Dashboard y Catálogo.

## Domain rules / invariants
Nuevas (en `domain/`, `ddd.md:283-288`, REQ-CUS-001/005/006):
- INV-01: `name` obligatorio: tras `strip()` no vacío; máximo 150 caracteres.
- INV-02: `phone`, `email` y `notes` son opcionales (vacíos por defecto). `email`, si existe, tiene formato válido y ≤ 254 caracteres; `phone` ≤ 30 caracteres; `notes` ≤ 2000.
- INV-03: el teléfono se guarda normalizado cuando es posible (regla de normalización abajo); si no es normalizable se guarda el texto recortado y **no** se rechaza.
- INV-04: un cliente nuevo nace activo; el estado solo cambia con `activate()`/`deactivate()` (idempotentes), no por asignación ni por `PATCH`.
- INV-05: el `id` (UUID) nunca cambia y no existe operación de borrado de clientes.
- INV-06: dos clientes pueden compartir teléfono (no hay unicidad en BD); el duplicado es una advertencia confirmable solo en el alta.
- INV-07: el dominio no importa Django; `customers` no importa `sales` ni `catalog`.

**Regla de normalización (`normalize_phone(raw, default_country_code)`)**: recortar; quitar espacios, guiones, puntos y paréntesis; si empieza con `+` se conserva; si empieza con `00` se reemplaza por `+`; si son solo dígitos se antepone `+` y el código de país por defecto; es normalizable si queda `+` y 8 a 15 dígitos; si no lo es, se devuelve el texto recortado original. No se elimina un `0` inicial de troncal (límite conocido).

## Acceptance criteria
- AC-01: `POST /api/customers/` con solo `name` responde 201 con el cliente `active=true` y `phone`, `email`, `notes` vacíos (`""`); aparece en `GET /api/customers/`. (REQ-CUS-001)
- AC-02: `name` ausente, vacío, solo espacios o de más de 150 caracteres → 400 con error en `name`; `email` con formato inválido o > 254 → 400 en `email`; `phone` > 30 → 400 en `phone`; `notes` > 2000 → 400 en `notes`. No se crea ni se modifica nada. Los errores de varios campos se devuelven juntos.
- AC-03: al crear o editar, un `phone` normalizable se guarda como `+<país><dígitos>` (p. ej. `76543210`, `+591 7654-3210`, `(591) 76543210` y `00591 76543210` → `+59176543210`; con país por defecto `591`); uno no normalizable (p. ej. `abc`, `123`, `76543210 int. 5`) se guarda recortado sin error. Un `phone` vacío se guarda como `""`.
- AC-04: duplicado en el alta: si `phone` es no vacío y otro cliente (activo o inactivo) tiene el mismo `phone` normalizado, y no viene `confirm_duplicate: true`, `POST` responde 409 `{code: "duplicate_phone", detail, matches[{id,name,phone,active}]}` (máx. 10) y **no crea** nada. Con `confirm_duplicate: true` crea (201). Sin teléfono no hay comprobación. `confirm_duplicate` no se persiste ni aparece en el recurso.
- AC-05: `PATCH /api/customers/{id}/` actualiza solo los campos enviados (`name`, `phone`, `email`, `notes`), refresca `updated_at`, conserva `id`, `active` y `created_at`; un `GET` posterior y la lista reflejan los cambios. Un cuerpo vacío responde 200 sin cambios. `active` en el cuerpo se ignora. `PATCH` no comprueba duplicados. (REQ-CUS-002)
- AC-06: `GET /api/customers/` soporta `search` (parcial, sin distinguir mayúsculas, por nombre; si el término contiene dígitos, también por teléfono comparando solo sus dígitos con `phone`, p. ej. `765 432` encuentra `+59176543210`), `active=true|false` (ausente = todos; otro valor → 400), combinación de ambos, `page` y `page_size` (máx. 100); orden por nombre e id. (REQ-CUS-003)
- AC-07: `POST .../deactivate/` deja `active=false` (idempotente); el cliente sigue existiendo, consultable por detalle y excluido de `?active=true`. `POST .../activate/` lo reactiva (idempotente). (REQ-CUS-005)
- AC-08: `GET /api/customers/{id}/` devuelve `id, name, phone, email, notes, active, created_at, updated_at`; id inexistente o que no es UUID → 404 `{detail}`. `DELETE` y `PUT` → 405. Sin token → 401 en todos los endpoints.
- AC-09 (menú): tras iniciar sesión el menú muestra "Dashboard", "Catálogo ▸ Producto" y "Cliente" (→ `/customers`, ícono `users`, sin submenú), traducidos en `en`, `es` y `de` (`es`: "Cliente").
- AC-10 (lista): `/customers` muestra `ngx-datatable` con Nombre (enlace al perfil), Teléfono, Correo, Estado (badge) y Acciones (ver, editar, activar/desactivar); buscador único "Buscar por nombre o teléfono" con debounce; selector de estado con **Activos preseleccionado** (Activos / Inactivos / Todos); botón "+" a `/customers/new`; paginación en servidor; estado vacío; teléfono/correo vacíos se muestran "—". Activar/desactivar pide confirmación (`sweetalert2`), actualiza la fila y avisa con `toastr`.
- AC-11 (formulario): `/customers/new` y `/customers/:id/edit` usan el mismo formulario (Nombre*, Teléfono, Correo, Notas); Reactive Form tipado; Guardar deshabilitado si es inválido o enviando; errores del servidor bajo cada campo; al guardar vuelve al perfil; Cancelar vuelve al perfil (edición) o a la lista (alta). El estado no es editable.
- AC-12 (duplicado en UI): si el alta recibe 409 `duplicate_phone`, se muestra un diálogo con las coincidencias (nombre, estado, enlace al perfil en pestaña nueva) y los botones "Crear de todos modos" (reenvía con `confirm_duplicate: true`, luego navega al perfil) y "Cancelar" (no crea, conserva los datos del formulario). Los nombres se muestran escapados.
- AC-13 (perfil): `/customers/:id` muestra nombre, teléfono, correo, notas, estado (badge), creado y actualizado; botones Editar, Activar/Desactivar (con confirmación) y Volver; una tarjeta "Historial de compras" con tabla Fecha/Total/Estado y, sin datos, el mensaje "Este cliente aún no tiene pedidos."; **no hace ninguna petición a pedidos**; un cliente inactivo se ve igual; cliente inexistente → aviso y retorno a la lista. (REQ-CUS-004, parcial)

## Edge cases
- EDGE-01: nombre con espacios alrededor → se guarda recortado.
- EDGE-02: dos formatos del mismo número (`76543210` y `+591 76543210`) se detectan como duplicados.
- EDGE-03: el duplicado coincide con un cliente inactivo → se avisa igualmente, con `active=false` en `matches`.
- EDGE-04: dos teléfonos no normalizables con el mismo texto recortado → se consideran duplicados.
- EDGE-05: más de 10 coincidencias → se devuelven 10.
- EDGE-06: búsqueda sin dígitos → solo por nombre; búsqueda vacía → sin filtro; `active` inválido → 400.
- EDGE-07: `PATCH` con `name: ""` → 400; `PATCH` de `phone` a `""` borra el teléfono.
- EDGE-08: el prefijo `+` con menos de 8 o más de 15 dígitos → no normalizable, se guarda recortado.
- EDGE-09: reenviar el alta con `confirm_duplicate: true` cuando ya no hay duplicado → crea normalmente.

## Error cases
400 `{campo: [mensajes en español]}` (forma y reglas); 404 `{detail: "Cliente no encontrado."}`; 405 en `DELETE`/`PUT`; 401 sin token; 409 solo en el alta por duplicado sin confirmar. Errores de red en la UI: aviso con `toastr`.

## Authorization / permissions
Sin roles: todo usuario autenticado puede todo (`IsAuthenticated` por defecto, `backend/config/settings/base.py:75-77`). El frontend no es la barrera de seguridad; la verificación real es el backend.

## API contract
- API-01: `/api/customers/` según `ADR-clientes-mvp-contrato-api`: `GET` lista `{count,next,previous,results[]}`, `POST` 201/409, `GET/PATCH /{id}/`, `POST /{id}/activate/`, `POST /{id}/deactivate/`. Recurso `{id, name, phone, email, notes, active, created_at, updated_at}` (opcionales ausentes = `""`). Rutas nuevas, sin romper contratos existentes.
- API-02 (contrato que Sales deberá cumplir, no se implementa): `GET /api/orders/?customer_id=<uuid>` paginado, por fecha descendente, con `id`, fecha, total (string decimal) y estado, también para clientes inactivos (`ADR-clientes-mvp-historial-compras`).

## UI behavior
- UI-01: menú, lista, formulario, perfil y diálogo de duplicado según el DDR. Estados: `loadingIndicator`, vacío, error de red (`toastr`), botón Guardar deshabilitado, errores de servidor por campo, 404 → aviso y retorno a la lista.
- UI-02: textos de pantallas en español; solo el menú usa `translate`. Acciones de tabla con los mismos colores e iconos que productos (ver el DDR de productos): Ver `#6777ef`, Editar `#ffc107`, Activar/Desactivar `#dc3545`.

## Non-functional requirements
- Seguridad: nombres de coincidencias escapados en el diálogo (sin inyección de HTML); sin datos personales en logs ni en URLs de navegación (solo ids).
- Precisión/localización: sin dinero propio; `total` del historial es un string decimal (se muestra sin aritmética con `float`).
- Compatibilidad: cambios aditivos; el setting nuevo tiene valor por defecto (no obliga a tocar `.env`).
- Privacidad: teléfono, correo y notas son datos personales; sin anonimización en el MVP (límite conocido).

## Out of scope
Pantalla y API de pedidos (Sales), conexión real del historial, creación rápida desde un pedido (solo diseñada), servicio `get_customer_for_sale`, campos futuros (`birthdate`, `address`, `tags`...), fusión de duplicados, comprobación de duplicados en `PATCH`, anonimización, permisos por rol, librería de teléfonos, extracción de estilos/`Page<T>` a `shared/`, purga de rutas de demo, i18n del contenido de las pantallas.

## Open questions
Ninguna bloquea la implementación:
- Código de país por defecto `591` (supuesto tomado de `ddd.md:271-273`); es configurable con `DEFAULT_PHONE_COUNTRY_CODE`. Pendiente de confirmación del negocio; cambiarlo no altera la Specification.
- Si `activate` (reactivar) es deseado además de `deactivate`: se incluye por el ADR; no contradice ningún REQ.
- REQ-CUS-001 (criterio "se asocia inmediatamente a un pedido") y REQ-CUS-004 (historial real) se cierran en el task de Sales.

# Test Specification

## Unit tests
- Backend dominio (`SimpleTestCase`, sin BD): `normalize_phone` con tabla de casos (AC-03, EDGE-08); validadores de nombre/correo/teléfono/notas (INV-01, INV-02, AC-02); `Customer.create`, `rename`, `change_contact`, `change_notes`, `activate`/`deactivate` idempotentes (INV-04); agregación de errores (AC-02).
- Backend aplicación (repositorio en memoria): `CreateCustomer` con/sin duplicado, con/sin `confirm_duplicate`, sin teléfono, coincidencia con inactivo (AC-04, EDGE-02/03/04/05/09); `UpdateCustomer` parcial sin tocar duplicados ni estado (AC-05); `ActivateCustomer`/`DeactivateCustomer`; `GetCustomer` inexistente.
- Frontend (Karma): `CustomersApiService` — mapeo DTO↔modelo, parámetros de lista, 400→errores por campo, 404, 409→`DuplicateCustomerError` con coincidencias, `create(input, true)` envía `confirm_duplicate`; componentes lista, formulario, perfil y sección de historial (AC-10..AC-13).

## Integration tests
- `APITestCase` con PostgreSQL y token: AC-01..AC-08 y EDGE-01..09 sobre `/api/customers/` (creación, validaciones, normalización persistida, 409 y confirmación, PATCH, búsqueda por nombre y por teléfono con separadores, filtro de estado, paginación y `page_size`, activar/desactivar, 404, 405, 401).
- Migración: `python manage.py makemigrations --check --dry-run` sin cambios pendientes y `migrate` aplica `customers.0001_initial`.

## E2E
**¿Corresponde E2E?** NO — no hay Playwright en `frontend/panel_admin/package.json` y agregarlo sería una dependencia nueva; las pantallas siguen un patrón ya probado (productos) y los tests de API y de componentes cubren cada AC. Se hace una verificación manual de humo (backend + `npm start`): menú → crear → duplicado → confirmar → editar → buscar → desactivar → ver filtro.

## Regression tests
- `layout/sidebar/sidebar-menu.spec.ts` hoy espera exactamente 2 entradas y 3 títulos: se actualiza a 3 entradas y 4 títulos (AC-09) manteniendo las aserciones de Dashboard y Catálogo.
- `python manage.py test` completo (accounts, catalog, config) debe seguir pasando; `ng lint` y `ng build` OK; los specs de `features/products` siguen pasando. La suite completa de Angular tiene fallos preexistentes de plantilla y `app.component.spec.ts` no compila en `main` (documentado en `TASK-catalogo-productos-mvp`): se verifican los specs de la feature.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | Backend integration test (`test_api`) + dominio |
| AC-02 | Backend unit (dominio) + integration test |
| AC-03 | Backend unit (tabla de `normalize_phone`) + integration (persistido) |
| AC-04 | Backend application test (repositorio en memoria) + integration test |
| AC-05 | Backend application test + integration test |
| AC-06 | Backend integration test (búsqueda, filtro, paginación) |
| AC-07 | Backend unit + integration test |
| AC-08 | Backend integration test |
| AC-09 | Angular unit test (`sidebar-menu.spec.ts`) |
| AC-10 | Angular unit test (`customer-list`) |
| AC-11 | Angular unit test (`customer-form`) |
| AC-12 | Angular unit test (`customer-form` + servicio) |
| AC-13 | Angular unit test (`customer-detail` y sección de historial) |

# Implementation Plan

## Architecture considerations
- ADR modelo-dominio: capas `domain/application/infrastructure/api` como `catalog`; dominio puro; normalización propia sin dependencia; `Protocol` de repositorio; sin unicidad en BD; setting `DEFAULT_PHONE_COUNTRY_CODE` (por defecto `591`) inyectado desde la API a los casos de uso.
- ADR contrato-api: vistas `APIView` delgadas que traducen errores; el 409 se devuelve como `Response` directa (no como `APIException`, para no convertir `active`/`id` a texto); paginación propia del módulo (sin importar `catalog.api`).
- ADR historial-compras: Customers no importa Sales; la sección de historial no hace peticiones.
- ADR frontend-feature: `features/customers` sin importar de `features/products`; `Page<T>` y estilos de acciones duplicados con deuda registrada.
- `ddd.md`: dominio sin Django; módulos sin importarse infraestructura; estados por métodos de la entidad; serializers validan forma y tipos (el correo se valida en el dominio, no con `EmailField`).
- Cambios aditivos; sin dependencias nuevas.

## Proposed solution
Replicar el patrón de `catalog` para Customers con estas piezas específicas: (1) funciones puras `normalize_phone` y validadores en el dominio; (2) `CreateCustomer` consulta `repository.find_by_phone` y lanza `DuplicateCustomerPhone` (excepción de aplicación con las coincidencias) salvo `confirm_duplicate`; (3) repositorio con búsqueda `Q(name__icontains) | Q(phone__contains=dígitos)` e índice no único en `phone`; (4) la vista de alta captura `DuplicateCustomerPhone` y responde 409; (5) frontend con un servicio que mapea 409 a `DuplicateCustomerError` y un formulario que abre `Swal` y reintenta con confirmación.

## Files/components affected
- **Backend** (`backend/modules/customers/`, nuevo):
  - `domain/{customer.py, exceptions.py, repositories.py}`
  - `application/{commands.py, queries.py, exceptions.py}`
  - `infrastructure/django/{models.py, mappers.py, repositories.py}`
  - `api/{serializers.py, views.py, urls.py, pagination.py}`
  - `apps.py`, `models.py` (re-exporta el modelo), `migrations/0001_initial.py` (generada), `tests/{test_domain.py, test_application.py, test_api.py}`
  - `backend/config/settings/base.py` (`INSTALLED_APPS`, `DEFAULT_PHONE_COUNTRY_CODE`), `backend/config/urls.py` (`api/customers/`), `backend/.env.example` (variable opcional documentada)
- **Frontend** (`frontend/panel_admin/src/`):
  - `app/features/customers/models/customer.ts`
  - `app/features/customers/services/customers-api.service.ts` (+ spec)
  - `app/features/customers/pages/{customer-list, customer-form, customer-detail}/` (componente, plantilla, scss de lista, spec)
  - `app/features/customers/components/customer-purchase-history/` (+ spec)
  - `app/features/customers/customers.routes.ts`, `app/features/customers/testing/customer-fixtures.ts`
  - `app/app.routes.ts` (ruta `customers`), `assets/data/routes.json`, `assets/i18n/{en,es,de}.json`, `app/layout/sidebar/sidebar-menu.spec.ts`
- **Documentación:** `docs/architecture/ddd.md` (endpoints `activate`/`deactivate` de clientes, como se hizo con productos), `CLAUDE.md` (mención de la variable opcional `DEFAULT_PHONE_COUNTRY_CODE`), TASK/PR.

## Implementation steps
1. **Dominio** (`customers/domain`): constantes, validadores, `normalize_phone`, entidad `Customer` con `create`, `rename`, `change_contact`, `change_notes`, `activate`, `deactivate`; `CustomerValidationError`, `CustomerNotFound`; `CustomerRepository` (`get`, `save`, `list`, `find_by_phone(phone, exclude_id=None, limit=10)`). Tests de dominio primero (AC-02, AC-03, AC-07; INV-01..05, 07).
2. **Aplicación**: `CreateCustomer` (con `default_country_code` y `confirm_duplicate`), `UpdateCustomer` (parcial, agrega errores, no guarda sin cambios), `ActivateCustomer`, `DeactivateCustomer`, `GetCustomer`, `ListCustomers`; `DuplicateCustomerPhone(matches)`. Tests con repositorio en memoria (AC-04, AC-05, EDGE-02..05, 09).
3. **Infraestructura**: `CustomerModel` (UUID, `name` 150, `phone` 30 con índice no único, `email` 254, `notes` texto, `active`, timestamps, `db_table='customers_customer'`, orden `name,id`), mapper, `DjangoCustomerRepository` con lista perezosa paginable, búsqueda por nombre/dígitos y `find_by_phone`; `apps.py`, `models.py`; registrar `modules.customers` en `INSTALLED_APPS`; `makemigrations customers` (AC-06).
4. **Settings**: `DEFAULT_PHONE_COUNTRY_CODE = env('DEFAULT_PHONE_COUNTRY_CODE', default='591')` en `base.py`; variable opcional en `.env.example` (sin tocar `.env`).
5. **API**: serializers (forma/tipos; `confirm_duplicate` solo en alta), vistas (`_run`, 409 directo), paginación (máx. 100), urls; `path('api/customers/', include(...))` en `config/urls.py` (AC-01..AC-08, API-01). Tests de integración.
6. **Frontend base**: `models/customer.ts` (`Customer`, `CustomerInput`, DTO, `Page<T>`, `CustomerOrderSummary`, `CustomerApiError`, `DuplicateCustomerError`), `customers-api.service.ts` (list/get/create(input, confirmDuplicate)/update/activate/deactivate; mapeo 400/404/409/red) y su spec (AC-12 parte servicio).
7. **Páginas**: `customer-list` (AC-10; estilos de acciones copiados), `customer-form` (AC-11, AC-12; diálogo `Swal` con nombres escapados), `customer-detail` + `components/customer-purchase-history` (AC-13); `customers.routes.ts` (`''`, `new`, `:id/edit`, `:id`) y ruta `customers` en `app.routes.ts`. Specs de cada una.
8. **Menú**: entrada "Cliente" en `routes.json` y claves `MENUITEMS.CUSTOMER.TEXT` en `en/es/de`; actualizar `sidebar-menu.spec.ts` (AC-09).
9. **Documentación**: actualizar `ddd.md` (endpoints de clientes) y `CLAUDE.md` (variable opcional).
10. **Verificación propia**: `python manage.py test`, `makemigrations --check --dry-run`, `ng lint`, `ng build`, specs de la feature; humo manual descrito en E2E.

## Database / migrations
Nueva migración `customers/migrations/0001_initial.py` (`CreateModel` + índice en `phone`), generada con `makemigrations`; solo tablas nuevas, reversible. No toca otras apps. Rollback: `migrate customers zero` o revertir el PR.

## Risks
- Normalización de teléfono incorrecta para formatos no previstos (p. ej. `0` troncal): mitigado con tabla de casos y el criterio "no normalizable se guarda tal cual"; límite documentado.
- Supuesto de país `591`: configurable por setting; sin impacto estructural si cambia.
- Carrera entre dos altas simultáneas con el mismo teléfono: aceptada (advertencia, no restricción).
- `Swal` con HTML: riesgo de inyección si no se escapan nombres; cubierto por AC-12 y un test.
- Búsqueda por teléfono con `contains` sin índice trigram: adecuado al volumen del MVP.
- Duplicación temporal de `Page<T>` y estilos de acciones respecto de `products`: deuda registrada en el ADR frontend.
- REQ-CUS-004 y el criterio de asociación a pedido no son verificables de extremo a extremo hasta Sales.

## New dependencies
Ninguna (pip ni npm). Sin Playwright.
