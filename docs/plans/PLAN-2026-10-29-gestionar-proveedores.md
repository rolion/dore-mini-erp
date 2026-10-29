# PLAN-2026-10-29-gestionar-proveedores (v1)

**Task:** TASK-gestionar-proveedores · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** [DDR pantallas-proveedores](../design/DDR-gestionar-proveedores-pantallas-proveedores.md) · [ADR modulo-proveedores](../adr/ADR-gestionar-proveedores-modulo-proveedores.md)

> COMPLETO por el eje 1 (reglas de dominio nuevas), el eje 2 (la fachada será consumida por Compras) y el eje 3 (contrato API, migración nueva, ADR y DDR).

## Objective
Entregar el módulo Compras → Proveedores: API `/api/suppliers/`, fachada para Compras y pantallas Angular de lista, formulario y detalle, aisladas por empresa y bloqueadas si `purchases` está deshabilitado.

## Context
Ver `docs/tasks/TASK-gestionar-proveedores.md`. Verificado sobre `main` (`bcf7382`): no existe `modules/purchases`; `purchases` es módulo habilitable de `modularity` (`domain/modules.py:28`); Compras es «Próximamente» (`app.routes.ts:81-89`); `customers` es la plantilla a seguir.

# Specification

## Domain context
**Bounded Context:** Purchases (nuevo). **Relacionados:** `modularity` (compuerta), futura task de Compras (consume la fachada). No se toca `expenses` ni `customers`.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Proveedor (`Supplier`) | Persona o empresa a la que se le compra | PB-COM-001 |
| Identificación (`tax_id`) | Documento fiscal o de identidad del proveedor (NIT/CI/RUC), texto libre | PB-COM-001 |
| Activo / inactivo | Si se ofrece en compras nuevas; no implica borrado | PB-COM-001 |
| Ver compras | Enlace al listado de Compras filtrado por el proveedor | PB-COM-001 |

Inconsistencias declaradas: UI en español («Proveedor», «Identificación»), API y dominio en inglés (`supplier`, `tax_id`).

## Current behavior
`/api/suppliers/` no existe; Compras abre «Próximamente»; el submenú de Compras es «Inicio» + «Configuración» (`routes.json:139-166`).

## Expected behavior
Un administrador de una empresa con Compras habilitado puede crear, editar, buscar, listar, consultar, activar y desactivar proveedores de su empresa. Nunca se borran. Compras podrá consultar por fachada un proveedor (con su estado) y los activos para su selector.

## Domain rules / invariants
- INV-01: `name` obligatorio (tras `strip()` no vacío), ≤ 150.
- INV-02: `tax_id` ≤ 50, `phone` ≤ 30, `notes` ≤ 2000, opcionales (vacíos por defecto, recortados); `email` opcional, ≤ 254, con formato válido si se informa.
- INV-03: un proveedor nace activo; `active` solo cambia con `activate()`/`deactivate()` (idempotentes), no por asignación ni por `PATCH`.
- INV-04: `id` inmutable; no existe operación de borrado.
- INV-05: sin unicidad de `tax_id`, nombre ni teléfono.
- INV-06: el dominio no importa Django; `purchases` no importa otros módulos de negocio.
- INV-07: toda consulta filtra por `company_id` del usuario autenticado, nunca del cliente.

## Acceptance criteria
- AC-01: `POST /api/suppliers/` solo con `name` → 201, `active=true`, resto `""`; aparece en la lista. (Criterio 1)
- AC-02: `name` ausente/vacío/solo espacios/> 150, `email` inválido o > 254, `tax_id` > 50, `phone` > 30 o `notes` > 2000 → 400 con error por campo (todos juntos); no se crea ni modifica nada. (Criterio 1; «validar correo cuando se informa»)
- AC-03: `PATCH /api/suppliers/{id}/` actualiza solo los campos enviados, refresca `updated_at`, conserva `id`, `active`, `created_at`; `active` en el cuerpo se ignora; `phone`/`tax_id`/`email`/`notes` a `""` los vacía; cuerpo vacío → 200 sin cambios.
- AC-04: `GET /api/suppliers/` soporta `search` (parcial, sin distinguir mayúsculas, por nombre **o** identificación), `active=true|false` (ausente = todos; otro valor → 400), combinación, `page` y `page_size` (máx. 100); orden nombre, id. (Criterio 2)
- AC-05: `POST …/deactivate/` y `…/activate/` cambian `active` (idempotentes); el proveedor sigue consultable por detalle y excluido de `?active=true` cuando está inactivo. No hay `DELETE`. (Criterio 2/3)
- AC-06: aislamiento: un proveedor de otra empresa no aparece en la lista, ni se obtiene, edita, activa ni desactiva (404); la empresa sale del usuario autenticado. (Criterio 2)
- AC-07: `GET /api/suppliers/{id}/` devuelve `id, name, tax_id, phone, email, notes, active, created_at, updated_at`; inexistente → 404 `{"detail": "Proveedor no encontrado."}`; `PUT`/`DELETE` → 405; sin token → 401; con el módulo `purchases` deshabilitado para la empresa → 403 `module_disabled`.
- AC-08 (fachada): `get_supplier_for_purchase(company_id, id)` devuelve `id, name, active` (también de un inactivo) o `None` si no existe o es de otra empresa; `list_active_suppliers(company_id, …)` devuelve solo activos de esa empresa. Así Compras puede rechazar inactivos en compras nuevas y mostrar históricos. (Criterio 3; la integración con compras reales queda para la task de Compras)
- AC-09 (menú): Compras muestra «Inicio», «Proveedores» (`/pocketbiz/purchases/suppliers`) y «Configuración», traducidos en `es`, `en`, `de`; solo visible con el módulo habilitado.
- AC-10 (lista): `/purchases/suppliers` con columnas Nombre (enlace), Identificación, Teléfono, Correo, Estado y Acciones (ver, editar, activar/desactivar, ver compras); búsqueda «por nombre o identificación» con debounce; filtro de estado con **Activos preseleccionado**; botón «Nuevo proveedor»; paginación en servidor; vacío; «—» en datos faltantes. Activar/desactivar pide confirmación (el texto de desactivar aclara que las compras históricas se conservan), refresca la fila y avisa con `toastr`.
- AC-11 (formulario): `/new` y `/:id/edit` con el mismo Reactive Form (Nombre*, Identificación, Teléfono, Correo, Notas); Guardar deshabilitado si es inválido o enviando; correo con formato inválido marcado junto al campo; errores del servidor bajo cada campo; al guardar vuelve al detalle; Cancelar vuelve al detalle (edición) o la lista (alta).
- AC-12 (detalle): `/:id` muestra todos los datos, badge de estado, creado/actualizado; botones Editar, Activar/Desactivar (con confirmación), Ver compras (`/purchases?supplierId=<id>`) y Volver; un proveedor inactivo se sigue mostrando; inexistente → aviso y retorno a la lista.

## Edge cases / Error cases
- EDGE-01: espacios alrededor se recortan en todos los campos de texto.
- EDGE-02: `email` vacío o solo espacios equivale a «sin correo».
- EDGE-03: dos proveedores con la misma identificación o el mismo nombre se permiten (INV-05).
- EDGE-04: valores no texto en un campo → 400 en ese campo.
- Errores: 400 `{campo: [mensajes]}`, 404 `{detail}`, 401, 403 (`module_disabled` o sin empresa), 405.

## Authorization / permissions
Solo administrador de empresa activa (`CompanyModulePermission`) y módulo `purchases` habilitado; `required_modules = ('purchases',)` en todas las vistas. El frontend (`moduleGuard`) no es la barrera.

## API contract
- API-01: `/api/suppliers/` según el ADR (lista paginada, `POST`, `GET/PATCH /{id}/`, `POST /{id}/activate|deactivate/`). Aditivo; no rompe contratos existentes.
- API-02: fachada `modules.purchases.services` (DTO `SupplierForPurchase`).

## UI behavior
- UI-01: menú, lista, formulario, detalle y diálogos según DDR y `design-system.md` §5 (Lista, Formulario, Detalle). Estados: cargando, vacío, error de red (`toastr`), errores de campo, 404 → aviso y retorno.
- UI-02: acciones con los colores/iconos de clientes; «Ver compras» con `shopping-bag`.

## Non-functional requirements
Texto de proveedores escapado por Angular (sin HTML crudo); sin datos personales en logs ni URLs (solo ids); sin dinero.

## Out of scope
Listado de Compras, creación de compras, selector real de nueva compra, pagos a proveedores, aviso de identificación duplicada, normalización de teléfono, vincular `expenses.supplier_name` con proveedores, importación/exportación, roles adicionales, bloqueo de desactivación (desactivar nunca está bloqueado).

## Open questions
No bloquean: (1) identificación sin unicidad ni aviso (confirmar con negocio); (2) «Ver compras» aterriza en «Próximamente» hasta la task de Compras.

# Test Specification

## Unit tests
- Dominio (`SimpleTestCase`): validadores y `Supplier.create/rename/change_contact/change_tax_id/change_notes/activate/deactivate` (INV-01..03, AC-02, EDGE-01/02/04); agregación de errores.
- Aplicación (repositorio en memoria): create/update parcial/get/list/activate/deactivate, inexistente → `SupplierNotFound`.
- Frontend (Karma): `SuppliersApiService` (mapeo `tax_id`↔`taxId`, parámetros de lista, 400→errores por campo, 404); componentes lista, formulario y detalle (AC-10..AC-12); `sidebar-menu.spec.ts` actualizado (AC-09).

## Integration tests
- `APITestCase` con PostgreSQL: AC-01..AC-07 en `/api/suppliers/` incluyendo dos empresas (AC-06) y módulo deshabilitado → 403 (AC-07).
- Fachada (AC-08): DTO de activo, inactivo, otra empresa, lista de activos.
- Guardas existentes: `test_guards.py` (company_id, `required_modules`, permiso por defecto) y `test_boundaries.py` pasan con el módulo registrado; `makemigrations --check` sin cambios pendientes.

## E2E
**NO** — no hay Playwright (sería dependencia nueva) y el patrón ya se prueba con API + componentes; verificación manual de humo: habilitar Compras → Proveedores → crear → buscar → desactivar → filtro → Ver compras.

## Regression tests
`python manage.py test` completo; `sidebar-menu.spec.ts`; `ng lint` y `ng build`; specs de `features/customers` intactos.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01, AC-03 | API integration + dominio/aplicación |
| AC-02 | Dominio unit + API integration |
| AC-04 | API integration (búsqueda, filtro, paginación) |
| AC-05 | Dominio unit + API integration |
| AC-06 | API integration con dos empresas |
| AC-07 | API integration (404/405/401/403) + `test_guards` |
| AC-08 | Test de fachada (`test_services.py`) |
| AC-09 | Angular unit (`sidebar-menu.spec.ts`) |
| AC-10 | Angular unit (`supplier-list`) |
| AC-11 | Angular unit (`supplier-form` + servicio) |
| AC-12 | Angular unit (`supplier-detail`) |

# Implementation Plan

## Architecture considerations
Ver ADR: capas como `customers`; vistas `APIView` delgadas con `required_modules`; paginación propia del módulo; fachada con DTO; frontend sin importar de `features/customers`.

## Files/components affected
- Backend: `modules/purchases/` (`__init__`, `apps.py`, `models.py`, `services.py`, `domain/{supplier,exceptions,repositories}.py`, `application/{commands,queries}.py`, `infrastructure/django/{models,mappers,repositories}.py`, `api/{urls,views,serializers,pagination}.py`, `migrations/0001_initial.py`, `tests/`); `config/settings/base.py`; `config/urls.py`; `modules/sales/tests/test_boundaries.py`; `modules/accounts/test_guards.py`.
- Frontend: `features/purchases/` (models, services, pages supplier-list/form/detail, routes, testing); `app.routes.ts`; `assets/data/routes.json`; `assets/i18n/{es,en,de}.json`; `layout/sidebar/sidebar-menu.spec.ts`.
- Docs: `docs/architecture/ddd.md` (nota del módulo), `docs/design/design-system.md` (submenú de Compras), `docs/producto/modulos-implementados.md`.

## Implementation steps
1. Dominio `Supplier` + excepciones + puerto (INV-01..04, AC-02, AC-05).
2. Casos de uso create/update/get/list/activate/deactivate (AC-01, 03, 04, 05).
3. Modelo, mapper, repositorio por empresa y migración `0001` (INV-07, AC-06).
4. API: serializers, paginación, vistas con `required_modules`, URLs, registro en settings y `config/urls.py` (AC-01..07).
5. Fachada `services.py` (AC-08).
6. Registrar el módulo en `test_boundaries.py` y `test_guards.py`; tests backend de dominio, aplicación, API y fachada.
7. Frontend: modelo, servicio, rutas `purchases/suppliers` (la ruta `purchases` de «Próximamente» se mantiene), lista, formulario, detalle (AC-10..12).
8. Menú: `routes.json`, i18n es/en/de, actualizar `sidebar-menu.spec.ts` (AC-09).
9. Docs de arquitectura, diseño y producto; verificación manual de humo.

## Database / migrations
Una migración nueva `purchases.0001_initial` (tabla `purchases_supplier`); no se edita ninguna migración existente.

## Risks
- Orden de rutas: `purchases/suppliers` debe declararse sin chocar con `purchases` y `purchases/settings`.
- Módulo `purchases` deshabilitado por defecto: las pruebas de API deben habilitarlo (ver `modularity/tests/test_enforcement.py`).
- Los AC de compras reales (selector, histórico) no pueden probarse de extremo a extremo hasta la task de Compras.

## New dependencies
Ninguna.
