# TASK-habilitar-modulos-por-empresa: Habilitar módulos por empresa (PB-MOD-001)

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-habilitar-modulos-por-empresa
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/15

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-27 | (nuevo) → INVESTIGATION | Task creado; `main` ya estaba al día | delivery-start |
| 2026-10-27 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | NEEDS_ARCHITECTURE (nuevo modelo por empresa, contrato API y navegación) | delivery-start |
| 2026-10-27 | PLANNING → ENGINEERING | Specification READY tras respuestas del usuario (ver Plan) | delivery-start |
| 2026-10-27 | ENGINEERING → REVIEW | Implementación completa según plan v1 | delivery-build |
| 2026-10-27 | REVIEW → PUBLISH | Quality Gate PASS (3 hallazgos Low abiertos); a la espera de aprobación humana | delivery-publish |

## Investigación

### Requerimiento
PB-MOD-001 · Habilitar módulos por empresa (Modularidad, P0). Como administrador, quiero habilitar los módulos que necesita mi empresa. Menú Configuración → Módulos (`/settings/modules`), solo admin de la empresa. Muestra nombre, descripción breve, estado, dependencias obligatorias y disponibilidad de integración opcional. Acciones Habilitar/Deshabilitar; módulos base sin interruptor; diálogo de confirmación con módulo, empresa y dependencias afectadas. Al habilitar Inventario y recargar aparece su menú solo en esa empresa; con dependencias faltantes se muestran sus nombres y la acción queda bloqueada. Cada empresa conserva su selección; Acceso/Empresa y Catálogo son base; Ventas, Clientes, Gastos, Reportes, Compras e Inventario tienen dependencias explícitas; no instala código ni migra por empresa. La desactivación segura se completa en PB-MOD-004.

**Aclaraciones del usuario (2026-10-27):**
1. Mapa de dependencias = propuesta del código: Ventas→Catálogo (opcional Clientes); Clientes→ninguna; Gastos→ninguna; Reportes→Ventas y Gastos (opcional Clientes); Compras→Catálogo y Gastos; Inventario→Catálogo (opcional Ventas, Compras).
2. Compras e Inventario son habilitables y su menú apunta a una pantalla placeholder «Próximamente».
3. Empresas existentes y nuevas arrancan con Catálogo, Clientes, Ventas, Gastos y Reportes habilitados; Compras e Inventario deshabilitados.
4. Esta historia oculta menú y rutas; el bloqueo 403 en la API de negocio y la desactivación segura quedan para PB-MOD-004.

### Hechos encontrados
- `backend/modules/accounts/models.py:9` — `Company` (UUID, `is_active`); `User.company`/`role` en `:34-40`. No existe ningún concepto de módulo habilitado.
- `backend/modules/accounts/api/permissions.py:4` — `CompanyAdminPermission` es el permiso por defecto de DRF (`config/settings/base.py:86`): autenticado, empresa activa y rol admin. Sirve tal cual para «vista exclusiva del administrador».
- `backend/shared/tenancy.py:13` — `company_id_from(request)` obtiene la empresa del usuario autenticado; los módulos de negocio no importan `accounts` (`docs/architecture/ddd.md:842`).
- `backend/config/settings/base.py:20-25` y `backend/config/urls.py:11-19` — un app y un prefijo `/api/...` por módulo (`products`, `customers`, `orders`, `expenses`, `expense-categories`, `reports`).
- `docs/architecture/ddd.md:819` — dependencias permitidas hoy: `sales → {catalog, customers}`, `reporting → {sales, expenses, customers}`; las tablas raíz usan `company_id` UUID indexado sin FK entre módulos (`ddd.md:844`). Migraciones `0002_company_id.py` de cada módulo siguen ese patrón.
- `frontend/panel_admin/src/assets/data/routes.json` — el menú lateral es estático (6 ítems: Dashboard, Catálogo, Cliente, Pedidos, Gastos, Reportes); `layout/sidebar/sidebar.service.ts:17` lo carga por HTTP y `sidebar.component.ts:109` lo asigna sin filtrar. `layout/sidebar/sidebar-menu.spec.ts` fija su contenido.
- `frontend/panel_admin/src/app/app.routes.ts:11-50` — rutas de negocio con `AuthGuard` (`core/guard/auth.guard.ts`), sin noción de módulo ni de rol.
- `frontend/panel_admin/src/app/core/models/user.ts` / `core/service/auth.service.ts:97-120` — el usuario guardado trae `role` y `company {id,name}`; no hay datos de módulos.
- `frontend/panel_admin/src/app/features/expenses/components/category-dialog/` — diálogo modal con `NgbActiveModal`, patrón a seguir para la confirmación.
- `docs/design/design-system.md:5-6` — plantillas Lista/Detalle; sección 6 documenta el menú actual (hay que actualizarla).
- `docs/producto/modulos-implementados.md` — Compras e Inventario no existen en el producto.

### Hipótesis / supuestos no confirmados
- «Deshabilitar» en esta historia solo impide dejar dependientes huérfanos (no se puede deshabilitar un módulo si otro habilitado lo requiere); no valida datos existentes ni bloquea la API: eso es PB-MOD-004 (confirmado por el usuario el alcance, la regla de dependientes es decisión de diseño propia).
- Un usuario sin empresa no llega a esta API (403 por `CompanyAdminPermission`).
- Si Reportes se deshabilita, el Dashboard (`/dashboard/main`) pertenece a Reportes y se oculta; el destino de redirección tras login pasa a ser el primer ítem visible.

### Módulos y dependencias relacionadas
Accounts (identidad, `Company`), todos los módulos de negocio (solo como claves del catálogo de módulos; ninguno se importa), frontend `layout/sidebar`, `app.routes.ts`, `core/`.

### Implementaciones similares existentes
- Backend: vista/casos de uso de `catalog` (`api/views.py`, `application/`, `infrastructure/django/repositories.py` con `company_id` en el constructor).
- Frontend: `features/expenses` (lista de categorías + `category-dialog`, servicio API, modelos).

### Comportamiento actual
Todo usuario admin ve y usa todos los módulos; el menú es idéntico para todas las empresas.

### Restricciones
`CLAUDE.md`: aislamiento por `company_id` desde el usuario autenticado, módulos de negocio no importan `accounts`, no editar migraciones aplicadas, sin dependencias nuevas sin avisar, textos en español, DDD pragmático.

### Riesgos identificados
- Ocultar el menú no protege la API (aceptado hasta PB-MOD-004; el DDR y el ADR lo dejan explícito).
- Condición de carrera al sembrar los valores por defecto de una empresa (mitigada con unicidad y `ignore_conflicts`).
- Deshabilitar Reportes deja sin Dashboard: la redirección post-login debe no apuntar a una ruta oculta.
- Pantalla placeholder para módulos inexistentes: riesgo de confundir al usuario; el texto debe decir «Próximamente».

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — introduce un modelo por empresa nuevo, un contrato API que consume el menú, cambia la navegación global y toca autorización de vistas; afecta a todos los módulos como catálogo.

### Diseño requerido
**SI** — pantalla nueva, diálogo de confirmación y cambio del menú lateral.

## Diseño
`docs/design/DDR-habilitar-modulos-por-empresa-pantalla-modulos.md`

## Arquitectura
`docs/adr/ADR-habilitar-modulos-por-empresa-modelo-y-contrato.md`

## Plan
`docs/plans/PLAN-2026-10-27-habilitar-modulos-por-empresa.md` (v1, COMPLETO) · Specification readiness: READY

## Implementación
**Backend** (`backend/modules/modularity/`): dominio puro con catálogo y reglas (INV-01..03, INV-06), modelos `CompanyModuleModel`/`CompanySettingsModel` y migración `0001_initial` (solo `CreateModel`, AC-09), repositorio `DjangoCompanyModuleRepository(company_id)` con sembrado idempotente en la primera lectura (AC-08, EDGE-03), casos de uso y API `GET /api/modules/`, `POST .../enable|disable/` (API-01..03; 404, 400 base, 409 con `missing`/`dependents`). Registro en `INSTALLED_APPS` y `config/urls.py`; `modularity` se añadió a `NON_BUSINESS` en `test_boundaries.py`.
**Frontend:** `core/service/modules.service.ts` (estado + API), `core/guard/module.guard.ts` (`data.module`), filtrado del menú en `sidebar.component.ts` con campo `module` en `routes.json`, rutas `settings/modules`, `purchases`, `inventory`, i18n es/en/de, `features/settings/` con `ModuleListComponent`, `ModuleConfirmDialogComponent` y `ComingSoonComponent`. AC-04/05/07, UI-01..04, EDGE-04/05.
**Referencias de diseño:** lista basada en `category-list` (tabla Bootstrap simple, desviación declarada en el DDR), diálogo según `category-dialog`; badges `badge-outline`, botones `btn-primary`/`btn-warning`.
**Desviaciones:** `ModulesService` y el modelo viven en `core/` (no en `features/settings/`) porque los consumen el menú, el guard y `AuthService` (que limpia el estado al cerrar sesión). El estado `initialized` se guarda en una segunda tabla `modularity_company_settings` (prevista en el ADR).
**Verificación propia (no es el Quality Gate):** backend `test_domain`, `test_boundaries` y `test_guards` pasan (19 tests). Los tests de integración `modularity/tests/test_api.py` no corrieron en esa primera pasada por falta de `backend/.env`; tras la autorización del usuario se copió el `.env` y corrieron en el Quality Gate (ver Review). Frontend: `ng lint` y `ng build` OK; Karma: los specs nuevos y los de sidebar/core pasan; fallan 71 specs «should create» de pantallas demo de la plantilla (sin proveedor `ActivatedRoute`), y `app.component.spec.ts` no compila en `main` (`title` inexistente), ambos preexistentes y ajenos a esta tarea.
**Deuda técnica:** los 71 specs demo rotos y `app.component.spec.ts`; bloqueo 403 por módulo en la API (PB-MOD-004).

## Review
**Veredicto: PASS** (2026-10-27, subagente aislado).
- Backend: `modularity` 22 tests OK; suite completa 593 tests OK en 2 corridas del gate (una corrida previa del implementador mostró fallas intermitentes en `modules.sales.tests.test_repository`: orden de items/pagos y `updated_at` iguales; el diff no toca ese código → preexistente, limitación conocida). bandit sin hallazgos.
- Frontend: `npm run lint` OK, `npm run build` OK, Karma acotado 25/25 OK; suite completa 71 fallos preexistentes (demo «should create») y `app.component.spec.ts` no compila en `main`.
- No ejecutado: ruff/flake8/mypy (no instalados), `npm audit` (ENOLOCK, sin lockfile), inspección visual en navegador (móvil, oscuro) y prueba manual con dos empresas.
- **Corrección posterior (2026-10-27):** REV-01..03 resueltos. REV-01: `ModulesService.load()` comparte la petición en vuelo (`share` + `finalize`) con spec nuevo. REV-02: dos tests de conflicto de sembrado en `test_api.py` (fila insertada por otra lectura; empresa ya inicializada no se resiembra). REV-03: destino post-login documentado como decisión en el plan y etiqueta del diálogo «Se verán afectados». Verificado: `modularity` 24 tests OK, lint OK, build OK, Karma acotado 47/47 OK.
- Hallazgos Low (ahora resueltos): [REV-01](../reviews/REV-2026-10-27-habilitar-modulos-por-empresa-01.md) (doble GET en carga en frío), [REV-02](../reviews/REV-2026-10-27-habilitar-modulos-por-empresa-02.md) (EDGE-03 sin test de concurrencia), [REV-03](../reviews/REV-2026-10-27-habilitar-modulos-por-empresa-03.md) (redirección post-login con Reportes deshabilitado, texto «Afectados»).

## Publicación
PR #15 listo para aprobación humana; no se mergea. Cambio sensible: **base de datos** (migración `modularity/0001_initial`, solo esquema) y **autorización** (módulo por empresa, ADR-habilitar-modulos-por-empresa-modelo-y-contrato).
