# TASK-gestionar-proveedores: Gestionar proveedores (PB-COM-001)

**Etapa actual:** PUBLISH
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
| 2026-10-29 | ENGINEERING → REVIEW | Implementación y pruebas escritas | delivery-build |
| 2026-10-29 | REVIEW → PUBLISH | Quality Gate ciclo 2: PASS | delivery-publish |

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

**Resumen.** Nuevo bounded context `backend/modules/purchases/` con el agregado `Supplier`, API `/api/suppliers/`, fachada para Compras y feature Angular `features/purchases` (lista, formulario, detalle), más entrada de menú «Proveedores».

| Parte | Cubre |
|---|---|
| `domain/supplier.py`, `domain/exceptions.py`, `domain/repositories.py` | INV-01..06, AC-02, AC-05 |
| `application/commands.py`, `queries.py` | AC-01, AC-03, AC-04, AC-05 |
| `infrastructure/django/*` + `migrations/0001_initial.py` | INV-07, AC-06 |
| `api/*` + `config/urls.py` + `settings/base.py` | AC-01..AC-07 (`required_modules = ('purchases',)`) |
| `services.py` | AC-08 |
| `features/purchases/*`, `app.routes.ts` | AC-10, AC-11, AC-12 |
| `routes.json`, `i18n/{es,en,de}.json` | AC-09 |

**Pruebas escritas:** backend `purchases/tests/{test_domain,test_application,test_api,test_services}.py`; rutas de Compras añadidas a `modularity/tests/test_enforcement.py`; módulo registrado en `sales/tests/test_boundaries.py` y `accounts/test_guards.py`; frontend specs de servicio, lista, formulario y detalle, y `sidebar-menu.spec.ts` actualizado.

**Verificación propia (no es el Quality Gate):**
- Backend sin base de datos: `test_domain`, `test_application`, `test_boundaries`, `test_guards` → 33 tests OK; `makemigrations --check` sin cambios pendientes.
- **No se pudieron ejecutar los tests con base de datos** (`test_api`, `test_services`, `test_enforcement`): el entorno del worktree no tiene `DATABASE_URL`/credenciales y cargar el `.env` del repositorio principal fue denegado por política. `delivery-publish` debe correrlos.
- Frontend: `ng lint` OK; `ng build` OK; Karma (Chrome headless) sobre `features/purchases` y `sidebar-menu.spec.ts` → 40/40 (se excluyó `app.component.spec.ts` con un tsconfig temporal ya eliminado, por su fallo de compilación preexistente documentado en TASK-catalogo-productos-mvp).

**Desviaciones respecto al plan:** ninguna de alcance. El modelo añade el índice `purch_supplier_company_active` (ADR). La ruta `purchases/suppliers` se declara antes de `purchases/settings` en `app.routes.ts`.

**UI:** pantallas de referencia `features/customers/pages/{customer-list,customer-form,customer-detail}` (plantillas Lista/Formulario/Detalle del sistema de diseño). Sin componentes compartidos nuevos; se reutiliza `shared/models/page` y `shared/styles/table-actions`. Duplicación de patrón con clientes aceptada en el DDR.

**Deuda técnica:** `Page<T>`/estilos ya compartidos; la validación de correo está duplicada en dominio y formulario (como en clientes). Sin aviso de identificación duplicada (fuera de alcance).

**Documentación actualizada:** `docs/architecture/ddd.md`, `docs/design/design-system.md`, `docs/producto/modulos-implementados.md`.

## Review

**Quality Gate (ciclo 1, subagente aislado, 2026-10-29): PASS CONDICIONADO — no se declara PASS.** Sin hallazgos Critical/High/Medium; faltan verificaciones aplicables sin ejecutar.

Ejecutado con evidencia:
- Backend sin BD: `test_domain`, `test_application`, `test_boundaries`, `test_guards` → 33 tests OK; `makemigrations --check` → sin cambios; `bandit -r modules/purchases` → sin issues; `py_compile` OK de los tests con BD.
- Frontend: `npm run lint` OK; `ng build` OK; Karma completo (sin `app.component.spec.ts`): 764 tests, 693 OK y 71 fallos, todos «should create» de componentes demo de la plantilla (`NG0201`), preexistentes y fuera del diff; `features/purchases` + sidebar + customers: 121/121 OK; cobertura de sentencias 82,63 %.
- Revisión de límites DDD, aislamiento por `company_id`, alcance (sin scope creep) y checklist visual por lectura de código: conforme.

**No ejecutado (bloquea el PASS):**
1. Tests con base de datos: `modules.purchases.tests.test_api`, `test_services`, `modules.modularity.tests.test_enforcement` y la regresión de `manage.py test` completo (sin `DATABASE_URL` real: `password authentication failed`). Cubren AC-01..AC-08 a nivel API/fachada.
2. `npm audit` (no hay lockfile).
3. Revisión visual en navegador (requiere backend con BD): no verificada.

Hallazgos (Low, sin REV): validación de correo duplicada entre dominio y formulario (deuda declarada, mismo patrón que clientes).

**Quality Gate (ciclo 2, subagente aislado): PASS.** Con `backend/.env` y PostgreSQL reales: `manage.py test --noinput` → 865 tests OK (86 s); subconjunto `purchases` + `test_enforcement` + `test_guards` + `test_boundaries` → 78 OK; `makemigrations --check` sin cambios; `bandit` sin issues; `git status` limpio; sin secretos en el diff. Cada AC-01..AC-08 tiene tests que corrieron (nombrados en el informe); AC-09..AC-12 verificados en el ciclo 1 (Karma 121/121). Sigue **sin realizarse**: `npm audit` (sin lockfile) y la revisión visual en navegador.

Nota: en una corrida previa de la suite completa falló una vez `sales.tests.test_repository…test_item_order_is_preserved` (orden `created_at`/UUID no determinista, archivo ajeno al diff); pasó 3/3 aislado y en el ciclo 2. Se arreglará en otra tarea.

## Publicación
PR #25 completo y listo para aprobación humana (no se mergea). Cambio sensible: **nuevo bounded context con migración (`purchases.0001_initial`)** respaldado por `ADR-gestionar-proveedores-modulo-proveedores`; rollback: revertir el PR o `migrate purchases zero`.
