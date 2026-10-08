# PLAN-2026-10-08-catalogo-productos-mvp (v1)

**Task:** TASK-catalogo-productos-mvp
**Modo:** COMPLETO
**DDRs relacionados:** [DDR-catalogo-productos-mvp-menu-y-pantallas-producto](../design/DDR-catalogo-productos-mvp-menu-y-pantallas-producto.md)
**ADRs relacionados:** [modelo-dominio](../adr/ADR-catalogo-productos-mvp-modelo-dominio.md), [contrato-api](../adr/ADR-catalogo-productos-mvp-contrato-api.md), [frontend-feature](../adr/ADR-catalogo-productos-mvp-frontend-feature.md)
**Specification readiness:** READY

> Modo COMPLETO por el eje 3 (contrato API nuevo, migración nueva, tres ADR y un DDR con impacto visual) y por el eje 1 (reglas de dominio nuevas en el primer bounded context).

## Objective
Implementar el módulo Catálogo (REQ-CAT-001..005): API REST de productos en `backend/modules/catalog` y pantallas Angular de lista, alta/edición y detalle, con el menú lateral reducido a Dashboard + Catálogo ▸ Producto.

## Context
Ver `docs/tasks/TASK-catalogo-productos-mvp.md`. Verificado hoy sobre `main` (179dc70): `backend/modules/` solo tiene `accounts`; `config/urls.py` solo monta `admin/`, `api/health/` y `api/auth/`; `INSTALLED_APPS` sin catalog; no existe `frontend/panel_admin/src/app/features/`; el menú sale de `src/assets/data/routes.json` (21 entradas). Nada cambió desde la investigación.

# Specification

## Domain context
**Bounded Context:** Catalog. **Related contexts:** Sales y Reporting consumirán Catalog a futuro (`ddd.md:753-770`), pero **no existen** y no se tocan.

## Ubiquitous language
| Term | Meaning | Source |
|---|---|---|
| Producto (`Product`) | Artículo comercializable del catálogo | REQ-CAT, `ddd.md:119` |
| `sale_price` / "precio de venta" | Importe `Decimal` ≥ 0, 2 decimales, una sola moneda implícita | REQ-CAT-001, ADR modelo-dominio |
| `active` / activo, inactivo | Si el producto puede venderse en nuevos pedidos | REQ-CAT-003 |
| "catálogo" | El conjunto de productos (activos e inactivos) consultable en la lista | REQ-CAT-001/004 |

Inconsistencias declaradas: la UI y los REQ dicen "Producto/Catálogo" (español), la API y el dominio usan `product`/`catalog` (inglés) — es intencional por convención del proyecto. `ddd.md:927` solo lista `deactivate`; se agrega `activate` (ADR contrato-api).

## Current behavior
No hay productos ni endpoint (`GET /api/products/` → 404, `backend/config/urls.py:6-10`). El menú muestra 21 entradas de demo (`routes.json`).

## Expected behavior
Un usuario autenticado puede crear, editar, listar (con búsqueda y filtro de estado), consultar y activar/desactivar productos, vía API y vía las pantallas; nunca se elimina un producto. El menú lateral muestra solo Dashboard y Catálogo ▸ Producto.

## Domain rules / invariants
Nuevas (todas en `domain/`, REQ-CAT-001/002/003, `ddd.md:176-181`):
- INV-01: `name` es obligatorio: tras `strip()` no puede quedar vacío; máximo 150 caracteres.
- INV-02: `sale_price` es `Decimal` ≥ 0, con ≤ 2 decimales y ≤ 9 999 999 999,99. Nunca `float`.
- INV-03: un producto nuevo nace activo.
- INV-04: el estado solo cambia mediante `activate()` / `deactivate()` (idempotentes); no por asignación ni por `PATCH`.
- INV-05: los productos nunca se eliminan (no existe operación de borrado).

## Acceptance criteria
- AC-01: Dado datos válidos (nombre y precio ≥ 0), `POST /api/products/` responde 201 con el producto `active=true`, y aparece en `GET /api/products/` y en la lista de la UI.
- AC-02: Dado nombre ausente, vacío o solo espacios, o de más de 150 caracteres, `POST` responde 400 con error en `name` y no se crea el producto.
- AC-03: Dado precio ausente, no numérico, negativo, con más de 2 decimales o fuera de rango, `POST`/`PATCH` responde 400 con error en `sale_price` y no se guarda nada. Precio `0` y `0.00` son válidos.
- AC-04: `PATCH /api/products/{id}/` con `name`, `description` y/o `sale_price` actualiza solo esos campos, refresca `updated_at`, y un `GET` posterior (y la lista) muestran los nuevos valores. Un `active` enviado en el cuerpo se ignora.
- AC-05: `POST .../deactivate/` deja `active=false`; el producto sigue existiendo, consultable por detalle y visible en la lista con `active=false` o sin filtro. `POST .../activate/` lo reactiva. Ambas son idempotentes (200 también si ya estaba en ese estado).
- AC-06: `GET /api/products/` soporta `search` (coincidencia parcial, sin distinguir mayúsculas, por nombre), `active=true|false` (sin parámetro = todos), combinación de ambos, `page`, `page_size` (máx. 100, default 50) y devuelve `{count, next, previous, results}` ordenado por nombre y luego id.
- AC-07: `GET /api/products/{id}/` devuelve `id, name, description, sale_price (string "35.00"), active, created_at, updated_at`; id inexistente o que no es UUID → 404.
- AC-08: `DELETE` y `PUT` sobre producto → 405; cualquier endpoint de productos sin token → 401.
- AC-09 (menú): tras iniciar sesión el menú muestra únicamente "Dashboard" (→ `/dashboard/main`, sin submenú) y "Catálogo" con el submenú "Producto" (→ `/catalog/products`), traducido en en/es/de.
- AC-10 (lista): `/catalog/products` muestra una tabla `ngx-datatable` con Nombre, Precio, Estado (badge verde "Activo"/rojo "Inactivo") y Acciones; buscador por nombre, selector Todos/Activos/Inactivos, botón "+" que lleva a `/catalog/products/new`; paginación y filtros se piden al servidor.
- AC-11 (acciones): desde la lista y el detalle se puede ver, editar y activar/desactivar; activar/desactivar pide confirmación (`sweetalert2`), luego actualiza la fila/pantalla y avisa con `toastr`.
- AC-12 (formulario): `/catalog/products/new` y `/catalog/products/:id/edit` usan el mismo formulario (Nombre*, Descripción, Precio*); el botón Guardar se deshabilita si es inválido o enviando; al guardar vuelve a la lista (alta) o al detalle (edición) con aviso; los errores 400 del servidor se muestran bajo cada campo; no hay campo de estado.
- AC-13 (detalle): `/catalog/products/:id` muestra solo lectura nombre, descripción, precio, estado (badge), creado y actualizado, con botones Editar, Activar/Desactivar y Volver; producto inexistente → aviso y retorno a la lista.

## Edge cases
- EDGE-01: nombre con espacios alrededor se guarda recortado; nombre de exactamente 150 caracteres es válido.
- EDGE-02: precios `"35"`, `"35.5"` y `"35.50"` son válidos; `"35.555"` (>2 decimales), `"-1"`, `"abc"` y `""` se rechazan; `"10000000000.00"` se rechaza por rango (máximo `9999999999.99`).
- EDGE-03: `PATCH` con cuerpo vacío es 200 sin cambios; `PATCH` con `name: ""` es 400.
- EDGE-04: dos productos con el mismo nombre son válidos (sin unicidad).
- EDGE-05: `search` vacío o ausente no filtra; `active=foo` (valor inválido) se trata como 400.
- EDGE-06: lista vacía → mensaje "No hay productos" en la UI.

## Error cases
- 400 `{campo: [mensaje, ...]}` en español para validación (mismo formato para forma y reglas de dominio); 404 `{detail}`; 401 sin token; 405 en métodos no soportados. Errores de red en la UI: aviso `toastr`, sin perder lo escrito en el formulario.

## Authorization / permissions
Solo requiere usuario autenticado por token (`IsAuthenticated`, ya por defecto). No hay roles: todo usuario autenticado puede todo. El frontend no es la barrera de seguridad; la aplica el backend. Sin cambios a autenticación.

## API contract
- API-01: contrato completo en el ADR contrato-api (rutas `/api/products/`, `{id}/`, `{id}/activate/`, `{id}/deactivate/`; query `search`, `active`, `page`, `page_size`). Es aditivo: no cambia contratos existentes. `sale_price` viaja como string decimal.

## UI behavior
- UI-01: según DDR: loading (`loadingIndicator`) en la lista, estado vacío, errores con `toastr`, confirmación `Swal` al activar/desactivar, badges `badge-outline col-green|col-red`, botón de acciones `btn-tbl-edit`, textos de las pantallas en español, menú traducido.
- UI-02: el precio se muestra tal como lo entrega la API (string con 2 decimales), sin símbolo de moneda ni aritmética en `float`.

## Non-functional requirements
- Precisión: dinero siempre `Decimal`/string, nunca `float` en backend; el formulario envía el valor como string.
- Compatibilidad: sin cambios en `/api/auth/*`, `/api/health/` ni en rutas de demo.

## Out of scope
SKU, moneda, `Money`, unicidad de nombre, eliminación de productos, roles/permisos finos, servicio de consulta para Sales, snapshot de pedidos y bloqueo en pedidos (Sales no existe), purga de rutas/componentes de demo de la plantilla, imágenes/categorías de producto, historial de cambios de precio, E2E con Playwright.

## Open questions
(No bloqueantes.) Símbolo/moneda a mostrar junto al precio (hoy ninguno); límite máximo de `description` (hoy sin tope, recortada con trim); si más adelante se quiere unicidad de nombre.

# Test Specification

## Unit tests
- Backend dominio (`SimpleTestCase`, sin BD): INV-01..04 y EDGE-01/02 sobre `Product` (crear, `rename`, `change_price`, `activate`/`deactivate` idempotentes, rechazo de `float`).
- Backend aplicación: casos de uso con un repositorio en memoria (crear, actualizar parcial, activar/desactivar, listar con `search`/`active`, no encontrado).
- Frontend: `ProductsApiService` con `HttpTestingController` (URLs, params `search`/`active`/`page`/`page_size`, cuerpo, errores 400 propagados con el mapa de campos); componentes `product-list`, `product-form`, `product-detail` con `TestBed` (render, validaciones, mensajes de servidor, confirmación y llamada de activar/desactivar, estado vacío).

## Integration tests
- Backend `APITestCase` + PostgreSQL con token: AC-01..08 y EDGE-03/04/05 (incluye paginación, orden, 405, 401, 404 con id no UUID).
- `python manage.py makemigrations --check --dry-run` sin cambios pendientes y `migrate` limpio.

## E2E
**¿Corresponde E2E?** NO — Playwright no está en `frontend/panel_admin/package.json` y agregarlo implicaría una dependencia nueva; el flujo queda cubierto por los tests de integración de API (contrato real con BD) y los tests de Angular contra `HttpTestingController`. Se hará una verificación manual de humo con backend + `npm start` (login → menú → crear → editar → desactivar → buscar/filtrar) en la etapa de review.

## Regression tests
`python manage.py test` completo (auth, health, config), `npm test` completo (incluye specs de sidebar y auth existentes), `npm run lint` y `npm run build` del frontend.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01, AC-02, AC-03 | Dominio (unit) + API integration test |
| AC-04, AC-05 | Dominio/aplicación (unit) + API integration test |
| AC-06 | Aplicación (unit con repositorio en memoria) + API integration test |
| AC-07, AC-08 | API integration test |
| AC-09 | Angular unit test (sidebar con `routes.json` real) + verificación manual |
| AC-10, AC-11 | Angular unit test `product-list` + servicio + verificación manual |
| AC-12 | Angular unit test `product-form` + servicio |
| AC-13 | Angular unit test `product-detail` + verificación manual |

# Implementation Plan

## Architecture considerations
Se respetan los tres ADR y `ddd.md`: dominio sin imports de Django; estados por métodos del agregado; serializers validan forma y tipos, las reglas viven en dominio; Catalog no importa otros módulos (`accounts` tampoco); Reporting/Sales no se tocan. Sin infraestructura nueva (no hay Docker/nginx en el repo para este alcance). Contrato aditivo; despliegue backend y frontend independiente (el frontend falla con aviso si la API no existe).

## Proposed solution
Capas según ADR modelo-dominio: entidad `Product` pura, casos de uso con repositorio inyectado (`Protocol`), repositorio Django + mapper, vistas `APIView` delgadas que traducen `ProductValidationError`→400 y no encontrado→404. La lista usa un envoltorio perezoso (`__len__` y `__getitem__` con slices que mapean filas ORM a entidades) para que `PageNumberPagination` pagine en servidor sin cargar todo. Frontend según ADR frontend-feature y DDR.

## Files/components affected
- **Backend (nuevo)** `backend/modules/catalog/`:
  - `__init__.py`, `apps.py` (`name='modules.catalog'`, `label='catalog'`), `models.py` (solo reexporta `ProductModel` para que Django lo registre).
  - `domain/{__init__,product.py,exceptions.py,repositories.py}`.
  - `application/{__init__,commands.py,queries.py}`.
  - `infrastructure/{__init__.py,django/{__init__,models.py,repositories.py,mappers.py}}`.
  - `api/{__init__,serializers.py,views.py,urls.py,pagination.py}`.
  - `migrations/{__init__,0001_initial.py}` (generada).
  - `tests/` (o `tests_*.py`) de dominio, aplicación y API.
- **Backend (editado)**: `config/settings/base.py` (`INSTALLED_APPS += 'modules.catalog'`), `config/urls.py` (`path('api/products/', include('modules.catalog.api.urls'))`).
- **Frontend (nuevo)** `frontend/panel_admin/src/app/features/products/`: `models/product.ts`, `services/products-api.service.ts` (+ spec), `pages/{product-list,product-form,product-detail}/` (ts/html/sass + spec), `products.routes.ts`.
- **Frontend (editado)**: `src/app/app.routes.ts` (ruta `catalog`), `src/assets/data/routes.json`, `src/assets/i18n/{en,es,de}.json`.
- **Docs**: `docs/architecture/ddd.md` (agregar `POST /api/products/{id}/activate` a la sección 14); `CLAUDE.md` solo si cambia algún comando (no se espera).

## Implementation steps
Fase A — Backend
1. Crear el esqueleto `modules/catalog` y registrarlo en `INSTALLED_APPS`; verificar que `manage.py check` pasa (importa un paquete llamado `django` dentro de `infrastructure/`; usar solo imports absolutos).
2. Dominio: `Product` (dataclass) con fábrica `Product.create(...)`, `rename`, `describe`, `change_price`, `activate`, `deactivate`; `ProductValidationError(errors: dict[str, list[str]])`; `ProductRepository` Protocol (`get`, `save`, `list(search, active)`). (INV-01..04, AC-02, AC-03.) Tests unitarios primero.
3. Aplicación: `CreateProduct`, `UpdateProduct` (cambios parciales), `ActivateProduct`, `DeactivateProduct`, `GetProduct`, `ListProducts`; excepción `ProductNotFound`. (AC-01, AC-04, AC-05, AC-06.)
4. Infraestructura: `ProductModel` (UUID pk, `name` 150, `description` texto en blanco permitido, `sale_price` `DecimalField(12,2)`, `active` default True, `created_at` auto_now_add, `updated_at` auto_now), mapper, repositorio con filtro `name__icontains` y `active`, orden `name, id`, envoltorio perezoso; generar `0001_initial` con `makemigrations catalog`.
5. API: serializers (entrada `name`, `description`, `sale_price` con `DecimalField(max_digits=12, decimal_places=2, min_value=0)`; salida con `id`, `active`, timestamps de solo lectura; `active` en entrada se ignora), `ProductPagination(page_size_query_param='page_size', max_page_size=100)`, vistas lista/alta, detalle/`PATCH`, `activate`, `deactivate` (rutas con `<uuid:pk>`; `DELETE`/`PUT` → 405), parseo de `active` (`true`/`false`, otro valor → 400) y de `search`; registrar en `config/urls.py`. (AC-01..08.)
6. Tests de API con token (`Token.objects.create` como en `accounts/tests.py`), `makemigrations --check`, suite completa.
7. Actualizar `ddd.md` sección 14 (`activate`).

Fase B — Frontend
8. Modelos (`Product`, `ProductInput`, `Page<T>`, `ProductFieldErrors`) y `ProductsApiService` (`list`, `get`, `create`, `update`, `activate`, `deactivate`, usando `environment.apiUrl`; errores 400 expuestos con su mapa de campos) + spec. (AC-10..13.)
9. Rutas: `products.routes.ts` (`''`→lista, `new`, `:id`, `:id/edit`) y `catalog` en `app.routes.ts` con `loadChildren`, `new` antes de `:id`.
10. `product-list`: `ngx-datatable class="material"` con `externalPaging`, `count/offset/limit`, buscador con debounce (`takeUntilDestroyed`), selector de estado, botón "+", acciones ver/editar/activar-desactivar con `Swal` y `toastr`, estado vacío y loading. (AC-10, AC-11, EDGE-06.)
11. `product-form` (alta y edición, `FormBuilder` tipado, validadores nombre requerido/máx. 150 y precio requerido/≥0; `input type="number" min=0 step=0.01`; envía precio como `string`; muestra errores del servidor bajo cada campo; navegación post-guardado). `product-detail` (solo lectura, acciones). (AC-12, AC-13.)
12. Menú: reducir `routes.json` a Dashboard + Catálogo ▸ Producto (iconos feather `monitor` y `package`), claves `MENUITEMS.*` en en/es/de; revisar que el spec de sidebar siga verde. (AC-09.)
13. `npm run lint`, `npm test`, `npm run build`; verificación manual de humo con backend + `npm start`.

Cada nueva regla de negocio (INV-01..04) tiene test en el paso 2/3/6; ningún paso de lógica queda sin test.

## Database / migrations
Una migración nueva `catalog/0001_initial` (solo `CreateModel`, reversible). Sin datos existentes ni backfill. Rollback: revertir el PR o `python manage.py migrate catalog zero`. No se edita ninguna migración existente.

## Risks
- Un paquete llamado `django` dentro de `infrastructure/` puede confundir imports relativos/auto-registro de modelos: mitigado con imports absolutos y `models.py` en la raíz del app que reexporta el modelo; si diera problemas, renombrar la carpeta a `orm` (desviación a registrar, ADR menciona `django/` por `ddd.md:2.2`).
- La paginación de DRF sobre un envoltorio no-QuerySet: cubierta por tests de lista/paginación.
- `ngx-datatable` con paginación externa tiene diferencias de API entre versiones (v22): revisar sus eventos `page`/`sort` al implementar.
- Los tests de backend requieren PostgreSQL accesible (regla del proyecto).
- Rutas de demo siguen accesibles por URL (deuda aceptada en ADR frontend-feature).

## New dependencies
Ninguna (pip ni npm).
