# TASK-gestionar-proveedores: Gestionar proveedores (PB-COM-001)

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-gestionar-proveedores
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/25

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-29 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-10-29 | INVESTIGATION → DESIGN | Veredicto NEEDS_ARCHITECTURE; diseño requerido | delivery-start |
| 2026-10-29 | DESIGN → ARCHITECTURE | DDR escrito | delivery-start |
| 2026-10-29 | ARCHITECTURE → PLANNING | ADR escrito | delivery-start |
| 2026-10-29 | PLANNING → ENGINEERING | Specification READY; PLAN v1 y PR abiertos | delivery-start |

## Investigación

### Requerimiento
PB-COM-001 · Gestionar proveedores (Módulo Compras, P1, dependencia PB-MOD-002). Como administrador, registrar proveedores para relacionar adquisiciones y pagos.

- Menú y vistas: Compras → Proveedores; listado, crear/editar y detalle. El historial de compras se consulta con el listado de Compras filtrado al proveedor.
- Columnas: nombre, identificación, teléfono, correo, estado. Buscar por nombre o identificación; filtrar activos/inactivos (activos por defecto).
- Formulario: nombre obligatorio; teléfono, correo, identificación y notas opcionales; correo validado si se informa; errores junto a cada campo.
- Acciones: Nuevo proveedor, Editar, Activar/Desactivar (con confirmación; no elimina compras), Ver compras.
- Interfaz: el selector de una nueva compra solo ofrece proveedores activos de la empresa; el detalle histórico sigue mostrando un proveedor desactivado.
- AC: crear/editar con nombre obligatorio y resto opcional; la lista busca y activa/desactiva solo proveedores de la propia empresa; un proveedor inactivo no se usa en compras nuevas y las compras históricas conservan su referencia.

### Hechos encontrados
- No existe `backend/modules/purchases/` (módulos: accounts, catalog, customers, expenses, inventory, modularity, reporting, sales). No hay compras ni proveedores como entidad; solo `supplier_name` (texto libre) en gastos: `backend/modules/expenses/domain/expense.py:37,53`.
- «Compras» ya es un módulo habilitable (`purchases`, requiere `catalog` y `expenses`, deshabilitado por defecto): `backend/modules/modularity/domain/modules.py:28`. En el frontend es una pantalla «Próximamente»: `frontend/panel_admin/src/app/app.routes.ts:81-89`; su submenú tiene «Inicio» y «Configuración»: `frontend/panel_admin/src/assets/data/routes.json:139-166`; `sidebar-menu.spec.ts:21-22` fija esas dos rutas.
- PB-MOD-002 está implementado: cada vista declara `required_modules` y el permiso por defecto es `CompanyModulePermission`; un test lo exige para toda ruta `api/…`: `backend/modules/accounts/test_guards.py:66-78`, `backend/modules/customers/api/views.py:61`.
- Referencia casi idéntica: `backend/modules/customers/` (domain/application/infrastructure/api, repositorio `DjangoCustomerRepository(company_id)`, activar/desactivar por método de la entidad, lista paginada con `search` y `active`, fachada `services.py`): `customers/domain/customer.py:99-145`, `customers/application/commands.py`, `customers/infrastructure/django/repositories.py:36-60`, `customers/services.py`, `customers/api/urls.py`.
- Modelo con `company_id` UUID sin FK, índice y `db_table` propia: `customers/infrastructure/django/models.py:6-24`. Las guardas exigen `company_id` en toda tabla raíz de `BUSINESS_APPS`: `accounts/test_guards.py:6,26-40`.
- Límites de arquitectura verificados por AST: `ALLOWED_DEPENDENCIES` en `sales/tests/test_boundaries.py:11-18` (hay que registrar el módulo nuevo).
- Frontend de referencia: `features/customers/` (`customers.routes.ts`, `pages/customer-list|form|detail`, `services/customers-api.service.ts`); filtro de estado «Activos» por defecto, búsqueda con debounce, confirmación con SweetAlert2: `customer-list.component.ts:19-120`. Plantillas de pantalla: `docs/design/design-system.md:105-123`.
- Las rutas de negocio llevan `moduleGuard` + `data.module`: `app.routes.ts:81-89`. Menú por `module` en `routes.json`; textos en `assets/i18n/{es,en,de}.json` (`MENUITEMS.PURCHASES`).

### Hipótesis / supuestos no confirmados
- La **identificación** (NIT/CI/RUC) es texto libre ≤ 50 caracteres, **sin unicidad ni aviso de duplicado** (el requerimiento no lo pide). Si negocio quiere aviso de duplicado, es un cambio de Specification posterior.
- El **teléfono** se guarda como texto recortado (≤ 30), sin normalización con código de país (a diferencia de Clientes, donde sirve para detectar duplicados; aquí no hay duplicados que detectar).
- El **listado de Compras**, el **selector de nueva compra** y las compras históricas **no existen todavía**. Esta task entrega lo que el proveedor debe ofrecer (API + fachada `get_supplier_for_purchase` y `list_active_suppliers`) y el enlace «Ver compras»; el cierre de extremo a extremo de los dos últimos criterios ocurre en la task de Compras.
- La tabla de proveedores es `purchases_supplier` y el app Django se llama `purchases` (igual a la clave del módulo).

### Módulos y dependencias relacionadas
`modularity` (compuerta del módulo `purchases`), `accounts` (empresa/rol vía `shared/tenancy.py`), futuro `purchases` (compras) consumirá la fachada. Sin acoplamiento con `expenses` en esta task (su `supplier_name` sigue siendo texto libre).

### Implementaciones similares existentes
`customers` (backend y frontend) y `catalog/products`.

### Comportamiento actual
`/api/suppliers/` no existe (404). Compras → «Próximamente». No hay entrada «Proveedores» en el menú.

### Restricciones
`CLAUDE.md`: aislamiento por `company_id`, dominio sin Django, módulos sin importarse infraestructura, estados por métodos del agregado, sin nuevas dependencias, no editar migraciones aplicadas.

### Riesgos identificados
- Nuevo bounded context: hay que registrar el app (`INSTALLED_APPS`, `config/urls.py`), los tests de límites y de guardas.
- Que el menú de Compras cambie rompe `sidebar-menu.spec.ts` (se actualiza).
- Dos criterios de aceptación dependen de entidades que aún no existen (compras); riesgo de sobreprometer. Mitigación: contrato de fachada probado + declaración explícita en la Specification.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — introduce un bounded context nuevo (`purchases`) con tabla, migración, contrato API y fachada para otro módulo futuro, además de pantallas nuevas.

### Diseño requerido
**SI** — tres pantallas nuevas (lista, formulario, detalle) y entrada de menú.

## Diseño
Ver `docs/design/DDR-gestionar-proveedores-pantallas-proveedores.md`.

## Arquitectura
Ver `docs/adr/ADR-gestionar-proveedores-modulo-proveedores.md`.

## Plan
`docs/plans/PLAN-2026-10-29-gestionar-proveedores.md` (v1, COMPLETO).

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
