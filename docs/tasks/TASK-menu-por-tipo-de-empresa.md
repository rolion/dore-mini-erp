# TASK-menu-por-tipo-de-empresa: Tipo de empresa al registrarse: módulos iniciales y orden del menú

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-menu-por-tipo-de-empresa
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/126

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-26 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-11-26 | INVESTIGATION → ARCHITECTURE | NEEDS_ARCHITECTURE: columna nueva en `Company`, contrato de registro y puerto de defaults | delivery-start |
| 2026-11-26 | ARCHITECTURE → DESIGN | ADR escrito; falta el diseño del selector y del menú | delivery-start |
| 2026-11-26 | DESIGN → PLANNING | DDR escrito | delivery-start |
| 2026-11-26 | PLANNING → ENGINEERING | Specification READY, PLAN v1 | delivery-start |
| 2026-11-26 | ENGINEERING → REVIEW | Implementación completa según PLAN v1 | delivery-build |

## Investigación

### Requerimiento
Organizar el menú según el tipo de empresa. Decisiones confirmadas por el usuario en el chat:
1. El tipo se elige **solo al registrarse**; no se cambia después.
2. El tipo es una **plantilla inicial**: define qué módulos se activan al crear la empresa. El admin puede activar o desactivar más módulos después desde Ajustes.
3. **Cotizaciones sigue siendo un módulo independiente.** En el menú de odontología se muestra como submenú «Presupuestos» dentro de Odontología (mismo módulo, otra etiqueta y ubicación).

Menús propuestos (Ajustes siempre al final):
- **Compraventa:** Inicio, Catálogo, Clientes, Ventas, Compras, Inventario, Contabilidad, Gastos, Reportes. Costeo opcional, apagado.
- **Servicios:** Inicio, Catálogo (servicios y productos), Clientes, Cotizaciones, Cobros, Agenda, Personal, Contabilidad, Gastos, Reportes.
- **Odontología:** Inicio, Catálogo, Clientes, Odontología (con Presupuestos), Cobros, Agenda, Personal, Contabilidad, Gastos, Reportes. Compras e Inventario de insumos opcionales, apagados.

### Hechos encontrados
- `backend/modules/accounts/models.py:9-30` — `Company` solo tiene `name`, `is_active` y `created_at`; no existe tipo de empresa.
- `backend/modules/accounts/registration.py:45` — el alta llama `company_defaults.apply_all(company.id)` sin parámetros; toda empresa nueva recibe el mismo snapshot.
- `backend/shared/company_defaults/snapshot.json` (sección `modularity`) — lista **los 14 módulos** no base: hoy toda empresa nueva nace con todo habilitado.
- `backend/modules/modularity/infrastructure/defaults.py:27-47` — `apply_modularity` habilita los módulos del snapshot y dispara `module_lifecycle.enabled`. Es la sección con `ORDER = 70`, la última.
- `backend/shared/company_defaults/__init__.py:69` — `apply_all(company_id, snapshot, *, dry_run)` no recibe contexto de empresa; `ctx` se crea adentro y es compartido entre secciones.
- `backend/modules/modularity/domain/modules.py:15-43` — catálogo de módulos con `requires`/`optional`; `DEFAULT_ENABLED_KEYS` solo se usa para la siembra perezosa de empresas sin `CompanySettingsModel`.
- `backend/modules/accounts/api/serializers.py:11-17` y `:20-32` — `RegisterSerializer` no tiene tipo; `UserSerializer.company` devuelve `{id, name}`.
- `backend/modules/accounts/api/views.py:46-64` — `RegisterView` pasa `validated_data` a `register_company_admin(**…)`.
- `frontend/panel_admin/src/assets/data/routes.json` — menú estático de 15 ítems de primer nivel con orden fijo; cada ítem puede llevar `module` y `adminOnly`. «Dashboard» y «Reportes» comparten `module: reporting`, así que `module` no identifica un ítem.
- `frontend/panel_admin/src/app/layout/sidebar/sidebar.component.ts:34-45,121-130` — `visibleRoutes` filtra por módulos (también en submenús) y rol; el menú combina `SidebarService.getRouteInfo()` con `ModulesService.enabledKeys$`.
- `frontend/panel_admin/src/app/layout/sidebar/sidebar-menu.spec.ts:23-30` — prueba que fija el orden y la cantidad (15) de ítems de `routes.json`.
- `frontend/panel_admin/src/app/authentication/signup/signup.component.ts:60-71` y `signup.component.html` — formulario reactivo con 7 campos; `AuthService.register` mapea errores por campo (`REGISTER_FIELD_BY_API_KEY`, `core/service/auth.service.ts:17`).
- `frontend/panel_admin/src/app/core/models/user.ts:14-39` — `UserCompany`, `RegisterInput` y `RegisterField`.
- `docs/design/design-system.md:213-214` y `:232-234` — plantilla de autenticación y reglas del menú dinámico.

### Hipótesis / supuestos no confirmados
- Las empresas existentes (todas con los 14 módulos) deben conservar su menú actual. Se les asigna el valor `general`, que no se ofrece en el registro. Si prefieres clasificarlas a mano, se puede hacer después en Django admin.
- Las secciones de defaults de módulos apagados (p. ej. Compras en una empresa de servicios) se siguen aplicando: crean filas de configuración inertes que evitan trabajo al habilitar el módulo más tarde. Se verifica en la construcción que no rompen nada.
- «Catálogo» conserva sus dos entradas (Productos y Servicios) en todos los tipos: Productos pertenece al módulo base `catalog` y no se oculta por tipo.

### Módulos y dependencias relacionadas
`accounts` (registro, `Company`), `shared/company_defaults` (puerto), `modularity` (catálogo de módulos y sección de defaults), frontend `authentication/signup`, `layout/sidebar`, `core/models/user`, `assets/data/routes.json`, `assets/i18n/{es,en,pt}.json`.

### Implementaciones similares existentes
- `TASK-registro-usuarios-empresa-multitenant` — alta de empresa con defaults atómicos.
- Defaults por empresa en `<módulo>/infrastructure/defaults.py` con `company_defaults.register`.

### Comportamiento actual
Cualquier empresa registrada obtiene los 14 módulos y el mismo menú de 15 ítems en orden fijo.

### Restricciones
- Los módulos de negocio no importan `accounts` (`CLAUDE.md`); `accounts` solo conoce el puerto `shared/company_defaults`.
- Nunca editar una migración aplicada: la columna nueva va en la migración `0003`.
- Texto visible solo por claves en las tres lenguas (`npm run i18n:check`).

### Riesgos identificados
- Ofrecer solo tres tipos deja a quien registra una empresa mixta con módulos de menos; mitigado porque el admin puede habilitar más desde Ajustes.
- Cambiar el contrato de registro rompe a cualquier cliente que no envíe el tipo; hoy el único cliente es la SPA.
- `apply_modularity` reutilizado por `copy_company_defaults` no debe cambiar de comportamiento.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — columna nueva y migración con datos existentes, cambio del contrato de registro y del puerto de defaults, y cambios coordinados en `accounts`, `modularity` y el frontend.

### Diseño requerido
**SI** — hay un campo nuevo en el registro y cambia la estructura visible del menú lateral.

## Diseño
Ver [DDR-menu-por-tipo-de-empresa-selector-y-menu](../design/DDR-menu-por-tipo-de-empresa-selector-y-menu.md).

## Arquitectura
Ver [ADR-menu-por-tipo-de-empresa-plantilla-inicial](../adr/ADR-menu-por-tipo-de-empresa-plantilla-inicial.md).

## Plan
Ver [PLAN-2026-11-26-menu-por-tipo-de-empresa](../plans/PLAN-2026-11-26-menu-por-tipo-de-empresa.md) (v1, COMPLETO, Specification READY).

## Implementación

**Resumen.** El registro exige `company_type` (`compraventa`, `servicios`, `odontologia`), lo guarda en `Company` y lo pasa como `profile` al puerto de defaults; la sección `modularity` habilita los módulos de la plantilla del tipo. El tipo viaja en `user.company.type` y el sidebar reordena `routes.json` con `arrangeRoutes`. Empresas existentes quedan `general` (migración `0003`, default).

**Cobertura por parte.**
- INV-01, AC-06: `accounts/models.py` (`CompanyType`, `company_type`, `REGISTRABLE_TYPES`), `migrations/0003_company_type.py`, admin con el tipo en solo lectura.
- INV-02/03: `modularity/domain/company_types.py` + `modularity/tests/test_company_types.py` (dependencias, contenido y paridad con `accounts`).
- AC-02/03/07: `shared/company_defaults/__init__.py` (`profile` en `ctx`), `modularity/infrastructure/defaults.py` (plantilla si hay perfil, snapshot si no).
- AC-01/04: `RegisterSerializer.company_type` (ChoiceField de los tres públicos) y `UserSerializer.company.type`.
- AC-05: `accounts/test_company_types.py` (habilitar y deshabilitar tras el alta).
- AC-08/12: signup (`select` con ayuda variable, error de servidor bajo el campo) e i18n es/en/pt.
- AC-09/10/11: `layout/sidebar/menu-layout.ts` (`arrangeRoutes`), `id` por ítem en `routes.json`, integración en `SidebarComponent`.
- Docs: `CLAUDE.md` y `design-system.md` (sección 6).

**Desviaciones respecto al plan.**
- `arrangeRoutes` se aplica **después** de `visibleRoutes` (el plan decía antes): así, si Odontología no está habilitada, Cotizaciones queda como ítem propio y no se pierde el acceso. Se agregó el test correspondiente.
- La prueba de integración de `data_import` registra con `compraventa` y habilita `costing` después: la valoración inicial es de Costeo, que ya no viene en todas las empresas.
- Se copió `backend/.env` del repo principal al worktree (ignorado por git) por indicación del usuario, para poder correr las pruebas.

**Deuda técnica / observaciones.** Dos listas deben mantenerse sincronizadas (`CompanyType` en `accounts` y `TEMPLATES` en `modularity`), protegidas por un test. «Productos» sigue visible en el catálogo de todos los tipos (fuera de alcance).

**UI.** Pantalla de referencia: plantilla «Autenticación» (`signup`) con `form-select` ya usado en el sistema; sin componentes compartidos nuevos.

**Verificación propia (no es el Quality Gate).** Frontend: `ng lint` limpio, `tsc` limpio, `i18n:check` 0 faltantes, 1866 pruebas Karma OK, `ng build` OK. Backend: `ruff` limpio en lo cambiado; `accounts`, `modularity` y `data_import` (238 pruebas) OK; suite completa 2514 pruebas OK.

## Review
_Pendiente_

## Publicación
_Pendiente_
