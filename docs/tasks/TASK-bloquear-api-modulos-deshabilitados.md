# TASK-bloquear-api-modulos-deshabilitados: Proteger las operaciones de módulos deshabilitados (PB-MOD-002)

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-bloquear-api-modulos-deshabilitados (creada desde `task/TASK-habilitar-modulos-por-empresa`, PR #15 sin mergear)
**Pull Request:** _sin abrir todavía_

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-27 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-10-27 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | NEEDS_ARCHITECTURE: autorización transversal en toda la API de negocio | delivery-start |
| 2026-10-27 | PLANNING → ENGINEERING | Specification READY tras respuestas del usuario | delivery-start |

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
`docs/plans/PLAN-2026-10-27-bloquear-api-modulos-deshabilitados.md` (v1, COMPLETO, Specification READY).

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
