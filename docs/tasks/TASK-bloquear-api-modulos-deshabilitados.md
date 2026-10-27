# TASK-bloquear-api-modulos-deshabilitados: Proteger las operaciones de módulos deshabilitados (PB-MOD-002)

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-bloquear-api-modulos-deshabilitados (creada desde `task/TASK-habilitar-modulos-por-empresa`, PR #15 sin mergear)
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/16 (apilado sobre PR 15)

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-27 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-10-27 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | NEEDS_ARCHITECTURE: autorización transversal en toda la API de negocio | delivery-start |
| 2026-10-27 | PLANNING → ENGINEERING | Specification READY tras respuestas del usuario | delivery-start |
| 2026-10-27 | ENGINEERING → REVIEW | Implementación completa según plan v1 | delivery-build |
| 2026-10-27 | REVIEW → DESIGN | Quality Gate FAIL: REV-01 High (DESIGN) | delivery-publish |
| 2026-10-27 | DESIGN → PLANNING → ENGINEERING | DDR complementario y plan v2 (AC sin cambios) | delivery-start |

## Investigación

### Requerimiento
PB-MOD-002 · Proteger las operaciones de módulos deshabilitados (Modularidad, P0, depende de PB-MOD-001). Como administrador, quiero que la API respete los módulos habilitados para impedir operaciones fuera de la configuración de mi empresa.
- Vista «Módulo no habilitado» (explicación breve y acción «Volver al inicio»); sin sesión se usa el login existente.
- Una petición rechazada no deja una tabla vacía que parezca un resultado válido ni conserva datos de otra empresa; un cambio de configuración durante la sesión actualiza los permisos efectivos.
- Abrir una URL deshabilitada o enviar su petición a mano no permite leer ni modificar datos; el backend comprueba aunque el botón no sea visible.
- AC: (1) un módulo deshabilitado rechaza consultas y escrituras de negocio aunque se invoque su URL; (2) la empresa sale de la sesión; (3) los accesos e integraciones comprueban módulo, empresa y rol; una dependencia opcional ausente no bloquea el flujo principal.

**Numeración:** en PB-MOD-001 este bloqueo se llamó PB-MOD-004. Queda así: **PB-MOD-002 = bloqueo en la API**; **PB-MOD-004 = desactivación segura de datos**. Los documentos vivos (`ddd.md`, `modulos-implementados.md`) se corrigieron; los registros de PB-MOD-001 (TASK/ADR/DDR/PLAN) conservan su texto histórico.

**Decisiones del usuario (2026-10-27):**
1. Con Clientes deshabilitado, Ventas y Reportes funcionan **sin integración**: no se puede asignar cliente (400) y los pedidos vinculados se muestran con `customer: null`.
2. Rechazo: **403** con `{detail, code: 'module_disabled', module}`.
3. Rama: **PR apilado** sobre el PR #15 (base = `task/TASK-habilitar-modulos-por-empresa`; al mergearse #15 se retargetea a `main`).

### Hechos encontrados
- `backend/config/settings/base.py:87-89` — el permiso por defecto de DRF es `CompanyAdminPermission`; ninguna vista de negocio comprueba el módulo.
- `backend/modules/accounts/api/permissions.py:6-16` — `CompanyAdminPermission`: autenticado, empresa activa y rol admin.
- `backend/modules/accounts/test_guards.py:48-64` — `DefaultPermissionTests` exige que toda vista `api/` no pública tenga exactamente `['CompanyAdminPermission']` como permisos.
- `backend/config/urls.py:9-19` — rutas `products`, `customers`, `orders`, `expenses`, `expense-categories`, `reports`, `modules`; `auth` y `health` son públicas.
- Vistas de negocio: catalog 4, customers 4, sales 10, expenses 7, reporting 7 (`backend/modules/*/api/views.py`).
- `backend/shared/tenancy.py:12-16` — `company_id_from(request)` toma la empresa del usuario autenticado, nunca del cliente.
- `backend/modules/modularity/infrastructure/django/repositories.py:16-23` — `enabled_keys()` siembra defaults y devuelve las claves de la empresa; el dominio expone `effective_enabled` (incluye los base).
- `backend/modules/modularity/api/views.py` — las vistas de módulos no deben quedar bloqueadas por sí mismas.
- `backend/modules/sales/infrastructure/adapters.py:11-12,27-40` — Sales llama a Customers solo por `services.py`; `backend/modules/sales/application/commands.py:18-23,47-48,67-68` valida `customer_id`; `backend/modules/sales/api/filters.py:53` filtra por `customer_id`.
- `backend/modules/reporting/infrastructure/adapters.py:11,72-73` y `application/queries.py:213-234` — Reporting lee nombres de clientes (top clientes y pendientes).
- `frontend/panel_admin/src/app/core/interceptor/error.interceptor.ts:15-21` — solo trata 401; un 403 llega al componente sin tratamiento común.
- `frontend/panel_admin/src/app/core/guard/module.guard.ts:7-30` — hoy redirige en silencio a `/catalog/products` (REV-03 de PB-MOD-001).
- `docs/architecture/ddd.md:844` — `modularity` no es un bounded context: ni los módulos de negocio ni `accounts` lo importan.

### Hipótesis / supuestos no confirmados
- Una o dos consultas extra por petición (leer módulos habilitados) son aceptables para esta escala.
- Solo existe el rol admin, así que «rol» se cumple con `CompanyAdminPermission` (no hay otro rol que probar).

### Módulos y dependencias relacionadas
catalog (base), customers, sales, expenses, reporting; `modularity` como fuente de verdad; `accounts` solo por el permiso por defecto.

### Implementaciones similares existentes
`CompanyAdminPermission` como permiso por defecto con guardas en `test_guards.py`; `DependencyConflict` en `modularity/api/views.py` como patrón de excepción con cuerpo extra.

### Comportamiento actual
Un módulo deshabilitado solo se oculta del menú y de las rutas Angular; todas sus URLs de API responden normalmente.

### Restricciones
Los módulos de negocio no importan `accounts` ni `modularity`; toda consulta filtra por `company_id`; no editar migraciones aplicadas; sin dependencias nuevas.

### Riesgos identificados
- Olvidar declarar el módulo en una vista nueva dejaría la ruta sin protección (mitigado con fail-closed y guarda).
- Rutas con dos módulos (top clientes necesita Reportes y Clientes).
- Consultas extra por petición.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — cambia la autorización de toda la API de negocio y su contrato de error, y cruza varios módulos (Sales y Reporting leen Customers).

### Diseño requerido
**SI** — hay una pantalla nueva («Módulo no habilitado») y cambia el flujo ante un rechazo.

## Diseño
Ver `docs/design/DDR-bloquear-api-modulos-deshabilitados-pantalla-no-habilitado.md`.

## Arquitectura
Ver `docs/adr/ADR-bloquear-api-modulos-deshabilitados-permiso-por-modulo.md`.

## Plan
`docs/plans/PLAN-2026-10-27-bloquear-api-modulos-deshabilitados.md` (v2, COMPLETO, Specification READY; v2 agrega UI-05, ACs sin cambios).

## Implementación
**Resumen.** Permiso por defecto `CompanyModulePermission` (`backend/config/permissions.py`) que, tras autenticación/empresa/rol, exige los módulos declarados en `required_modules` de cada vista (fail-closed si falta) y responde 403 `{detail, code: 'module_disabled', module}`. Puerto neutro `backend/shared/module_gate.py`, registrado por `modularity` en `AppConfig.ready()` (`infrastructure/django/gate.py`). Ventas y Reportes consultan el puerto para la integración opcional con Clientes. Angular: pantalla `/module-disabled`, `moduleGuard` e interceptor 403.

**Cobertura.**
- AC-01, AC-06, INV-02: `required_modules` en las 32 vistas de negocio y en las de `modularity`; `test_enforcement.DisabledModuleTests` recorre todas las rutas de negocio por método.
- AC-02: suite completa existente.
- AC-03, INV-01: `CompanyIsolationTests` (otra empresa, `company_id` enviado por query/cabecera).
- AC-04, AC-11: `ConfigurationChangeTests`.
- AC-05: orden auth → empresa → módulo.
- AC-07, AC-08: `CustomersOptionalIntegrationTests`, `GetPendingOrders` sin nombres y `top-customers` exige también `customers`.
- AC-09: `accounts/test_guards.py` (permiso por defecto y `required_modules` conocido).
- AC-10, AC-12: specs de interceptor, guard y `ModuleDisabledComponent` (sin sesión sigue el 401 → login existente).
- EDGE-01/02/05: tests de `test_api`, `test_enforcement` y `test_gate`.

**Desviaciones respecto al plan.**
- `ModulesService` y el modelo no cambiaron.
- `enabled_keys()` ahora lee primero las filas existentes (una consulta en el camino habitual) y solo siembra si no hay ninguna; el plan preveía la lectura previa de PB-MOD-001 (2 consultas). Motivo: reducir el costo por petición.
- Los adaptadores de Ventas y Reportes memorizan `is_available()` por instancia (una consulta por petición).
- `test_list_does_not_query_per_row` pasa de 5 a 7 consultas (módulos en el permiso + módulos de Clientes): costo conocido de este diseño.
- `test_seed_ignores_rows_inserted_by_a_concurrent_read` (PB-MOD-001) se reescribió para simular una primera lectura obsoleta, porque con la lectura previa una fila suelta ya cuenta como empresa inicializada.

**Pantalla de referencia / componentes.** `coming-soon` (pantalla simple); `ModuleDisabledComponent` reutiliza breadcrumb, `.card` y `btn btn-primary`; sin componentes nuevos en `shared/`.

**Verificación propia (no es el Quality Gate).** Backend: 620 tests, pasan salvo los dos tests intermitentes preexistentes de `modules.sales.tests.test_repository` (orden de items/pagos). Frontend: `npm run lint` y `npm run build` OK; Karma acotado (core, settings, sidebar) 53/53. No se hizo inspección visual en navegador.

**Deuda técnica.** Tests intermitentes de `sales.test_repository`; el enlace «Volver al panel» de `coming-soon` y el destino post-login siguen en `/dashboard/main` (REV-03 de PB-MOD-001, resuelto documentando que `moduleGuard` redirige).

**Ciclo 2 (plan v2, tras el FAIL de REV-01..04).**
- REV-01 (High, DESIGN → UI-05): con Clientes deshabilitado, `CustomerOptionsService.search` no pide nada a la API; la lista y el formulario de pedidos ocultan el filtro y el selector de cliente, y Reportes oculta (y no pide) «Clientes con mayor compra». El interceptor no cambia. `ModulesService.isDisabled(key)` es solo verdadero con módulos cargados. Cubierto por specs de servicio, lista, formulario y reportes.
- REV-02 y REV-03 (Low): redacción del plan (`GateNotConfigured`; sin caché entre peticiones, una consulta en el permiso y una por adaptador).
- REV-04 (Low): `PermissionOrderTests` (401 sin token, empresa inactiva, HEAD y OPTIONS con módulo deshabilitado).
- Verificación propia (no es el Quality Gate): backend 623 tests OK; frontend lint y build OK y Karma acotado (sales, reporting, settings, core, sidebar) 253/253.

## Review
**Veredicto ciclo 1: FAIL** (2026-10-27, subagente aislado).
- Backend: `modularity` 47 tests OK; suite completa 620 tests OK en 2 corridas. Frontend: lint OK, build OK, Karma acotado 53/53 OK; Karma completo 71 fallos preexistentes (pantallas demo) ajenos al diff. bandit: 1 Low preexistente fuera del diff. `npm audit` no realizado (sin lockfile). Inspección en navegador no verificada.
- Autorización: sin bypass; las 32 vistas de negocio declaran el módulo correcto y el orden auth → empresa → rol → módulo se conserva.
- Hallazgos: [REV-01](../reviews/REV-2026-10-27-bloquear-api-modulos-deshabilitados-01.md) **High, DESIGN** (el interceptor expulsa a Pedidos/Reportes por peticiones opcionales a Clientes), [REV-02](../reviews/REV-2026-10-27-bloquear-api-modulos-deshabilitados-02.md) Low (excepción del puerto vs `ImproperlyConfigured`), [REV-03](../reviews/REV-2026-10-27-bloquear-api-modulos-deshabilitados-03.md) Low (no hay caché por petición), [REV-04](../reviews/REV-2026-10-27-bloquear-api-modulos-deshabilitados-04.md) Low (tests de AC-05 débiles).
- Retorno: el High es de categoría DESIGN → `delivery-start` (plan v2 y DDR complementario) → `delivery-build` → nuevo Quality Gate.

## Publicación
_Pendiente_
