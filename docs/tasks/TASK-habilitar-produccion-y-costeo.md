# TASK-habilitar-produccion-y-costeo: Habilitar Producción y Costeo con sus dependencias (PB-MOD-005)

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-habilitar-produccion-y-costeo
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/34

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-30 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-10-30 | INVESTIGATION → DESIGN | Veredicto NEEDS_ARCHITECTURE, diseño requerido | delivery-start |
| 2026-10-30 | DESIGN → ARCHITECTURE | DDR escrito | delivery-start |
| 2026-10-30 | ARCHITECTURE → PLANNING | ADR escrito | delivery-start |
| 2026-10-30 | PLANNING → ENGINEERING | Specification READY, plan v1 y PR abierto | delivery-start |
| 2026-10-30 | ENGINEERING → REVIEW | Implementación completa según plan v1 | delivery-build |

## Investigación

### Requerimiento
PB-MOD-005 · Módulo Modularidad · P1. Como administrador, habilitar **Producción** y **Costeo** por empresa para activar solo las capacidades necesarias.

- Dependencias de historia: PB-MOD-001 (módulos por empresa), PB-CAT-001 (usos del producto).
- Menú y vistas: Configuración → Módulos (ampliar la vista existente). Producción agrega Recetas, Elaboraciones, Envasados y Configuración. Costeo agrega Configuración, Costos por lote y Análisis.
- Datos: nombre, descripción, estado y dependencias. Producción requiere Catálogo e Inventario; Costeo requiere Producción y la capacidad de **valoración de Inventario** (PB-VAL-001/002). Compras no es obligatoria para producir.
- Acciones: Habilitar muestra dependencias faltantes. Desactivar explica órdenes abiertas y costos sin cerrar; no deshabilita otros módulos ni borra historial en silencio.
- Criterios: (1) la librería opera sin Producción ni Costeo; Dore puede activar Producción sin Costeo; (2) API y menú respetan los módulos de la empresa y, sin valoración, no se habilita Costeo ni se muestran costos supuestamente completos; (3) se bloquea desactivar Inventario con Producción activo, y Producción con Costeo activo u órdenes abiertas, informando cómo resolver; (4) activar Costeo no calcula retroactivamente: se fija una fecha de adopción y se valoran las existencias actuales.

### Hechos encontrados
- El catálogo de módulos está en código y es inmutable: `backend/modules/modularity/domain/modules.py:15-26` (hoy `access`, `catalog` base; `customers`, `sales`, `expenses`, `reporting`, `purchases`, `inventory`). **No existen `production` ni `costing`.** `DEFAULT_ENABLED_KEYS` (`:31`) = customers, sales, expenses, reporting.
- Reglas puras de habilitación: `check_can_enable` / `check_can_disable` (`domain/modules.py:71-83`); solo conocen `requires` y dependientes habilitados; error `DependencyError(kind='missing'|'dependents')` (`:42-48`).
- Casos de uso `EnableModule` / `DisableModule`: `application/use_cases.py:46-75`; registran el cambio en el historial vía `_record` (`:29-35`). Son idempotentes (`:54`, `:70`).
- API: `GET /api/modules/`, `POST /api/modules/<key>/enable|disable/` — `api/views.py:58-78`; 409 con `{detail, missing}` o `{detail, dependents}` (`:45-46`, `:52-55`); serialización en `api/serializers.py:8-19`.
- Persistencia: una fila `CompanyModuleModel` por módulo no base habilitado, con `enabled_at` auto (`infrastructure/django/models.py:16-28`); deshabilitar **borra la fila** (`repositories.py:36-37`) y habilitar usa `get_or_create` (`:33-34`). Claves guardadas fuera del catálogo se ignoran (`effective_enabled`, `domain/modules.py:58-60`).
- Bloqueo de API por módulo: `config/permissions.py` (`CompanyModulePermission`, `required_modules` fail-closed) sobre el puerto neutro `shared/module_gate.py`, registrado en `modularity/apps.py`. El test `modules/accounts/test_guards.py` exige `required_modules` válidos contra el catálogo.
- Configuración por módulo: `_settings_module` acepta cualquier módulo no base del catálogo (`application/settings_use_cases.py:23-28`); un módulo sin ajustes devuelve lista vacía y la pantalla lo indica (`docs/producto/modulos-implementados.md` §3.8). El historial de módulos usa el ámbito `modules` (`:9`, `:122-123`).
- **No existe valoración de Inventario**: `grep` de «valoración/costo» en `backend/modules/inventory` y en `docs/` no encuentra implementación; PB-VAL-001/002 no están hechas. Inventario solo tiene existencias, movimientos y ajustes (`docs/producto/modulos-implementados.md` §2).
- **No existe Producción ni Costeo** (ni dominio, ni API, ni pantallas): `ls backend/modules` = accounts, catalog, customers, expenses, inventory, modularity, purchases, reporting, sales.
- **PB-MOD-004 (desactivación segura validando datos existentes) sigue pendiente**: `docs/producto/modulos-implementados.md` §3.7 y el diálogo de deshabilitar (`module-confirm-dialog.component.html`: «la desactivación segura completa llega en una próxima versión»).
- Frontend: pantalla `features/settings/pages/module-list/module-list.component.{ts,html}` calcula bloqueos solo desde `requires` y dependientes (`:70-86`); `ModulesService` publica el set de claves habilitadas que usan el menú (`routes.json`, campo `module`) y `moduleGuard`; modelo `core/models/module.ts`. El diálogo `module-confirm-dialog` muestra Módulo, Empresa, Requiere, Se verán afectados.
- Rutas de módulos aún sin pantallas usan `ComingSoonComponent` (`app.routes.ts:81-89`, `features/settings/pages/coming-soon`); la configuración sin ajustes reutiliza `module-settings` con `data.settingsModule` (`app.routes.ts:56-66`, `:97-105`). Menú con i18n `MENUITEMS.<MÓDULO>` en `assets/i18n/{es,en,de}.json`.
- Diseño: `docs/design/DDR-habilitar-modulos-por-empresa-pantalla-modulos.md` define la lista de módulos (tabla simple, bloqueos visibles, diálogo con `<dl>`).

### Hipótesis / supuestos no confirmados
- (S-1) «Capacidad de valoración de Inventario» no es un módulo sino una capacidad que Inventario ofrecerá cuando existan PB-VAL-001/002; se modela como **capacidad con proveedor registrado** (fail-closed: sin proveedor no está disponible). Hasta que PB-VAL se implemente, Costeo no se puede habilitar en ninguna empresa; es el comportamiento pedido («si falta valoración, no se habilita Costeo»).
- (S-2) «Órdenes abiertas» y «costos sin cerrar» pertenecen a Producción y Costeo, que aún no existen; esta historia entrega el **punto de extensión** (guardas de desactivación registradas por módulo) y su explicación en API/UI. Los módulos de Producción/Costeo registrarán sus guardas cuando existan; sin guardas registradas no hay bloqueo por datos.
- (S-3) «Se valoran existencias actuales» se entrega como **gancho de habilitación** (`on_enabled` con empresa y fecha de adopción, dentro de la misma transacción); la valoración en sí la implementa PB-VAL/Costeo.
- (S-4) La fecha de adopción es el `enabled_at` de la fila del módulo. Al deshabilitar se borra la fila, así que **una rehabilitación fija una fecha nueva** (coherente con «no calcular retroactivamente»); las anteriores quedan en el historial de cambios.
- (S-5) Producción y Costeo quedan **deshabilitados por defecto** (los defaults solo rigen para empresas aún no inicializadas y no cambian); la librería sigue igual sin acción.

### Módulos y dependencias relacionadas
`modularity` (catálogo, casos de uso, API, historial), `shared` (puerto nuevo), `inventory` (futuro proveedor de la capacidad de valoración; sin cambios aquí), `production` y `costing` (entradas de catálogo; sin código de negocio todavía), frontend `settings`, `core/models`, menú/rutas.

### Implementaciones similares existentes
Puerto neutro `shared/module_gate.py` (registro de proveedor en `AppConfig.ready`); dependencias y 409 de PB-MOD-001; configuración sin ajustes de Compras/Inventario; placeholder «Próximamente».

### Comportamiento actual
Solo 6 módulos no base habilitables; ninguna noción de capacidad, de bloqueo por datos ni de fecha de adopción en la API. Deshabilitar muestra un aviso genérico de PB-MOD-004.

### Restricciones
`CLAUDE.md`: módulos de negocio no importan `modularity`/`accounts`; `modularity` no importa módulos de negocio; sin migraciones por empresa; no editar migraciones aplicadas; avisar antes de instalar dependencias (no se necesita ninguna).

### Riesgos identificados
- Carrera entre desactivar Producción y crear una orden: la guarda definitiva debe vivir en Producción dentro de su transacción (a cargo de su historia); aquí se documenta el contrato.
- Costeo no habilitable hasta PB-VAL (esperado); las pruebas usan proveedores falsos.
- Contrato de `GET /api/modules/` crece (aditivo); el frontend viejo lo ignora.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — Introduce dos módulos nuevos en el catálogo, un puerto transversal en `shared` (capacidades, guardas de desactivación y gancho de habilitación), cambios de contrato API y reglas de dinero indirectas (adopción de costeo), con impacto sobre Inventario, Producción y Costeo futuros.

### Diseño requerido
**SI** — Cambia la pantalla Configuración → Módulos (capacidades, fecha de adopción, bloqueos explicados), el diálogo de confirmación y el menú con dos grupos nuevos.

## Diseño
`docs/design/DDR-habilitar-produccion-y-costeo-modulos-y-bloqueos.md`. Parte de la pantalla de módulos existente (tabla simple + diálogo); agrega capacidades en «Requiere», fecha de adopción, motivos de bloqueo con cómo resolverlos y dos grupos de menú con pantallas «Próximamente» y Configuración.

## Arquitectura
`docs/adr/ADR-habilitar-produccion-y-costeo-capacidades-y-bloqueos.md`. Catálogo con `production` y `costing`; puerto `shared/module_extensions.py` (capacidades, guardas, gancho); 409 ampliado; fecha de adopción = `enabled_at`; sin migración.

## Plan
`docs/plans/PLAN-2026-10-30-habilitar-produccion-y-costeo.md` (v1, COMPLETO). Specification readiness: **READY**.

## Implementación
**Resumen.** Backend: `production` y `costing` en el catálogo (`domain/modules.py`, con `requires_capabilities`/`records_adoption`, `CAPABILITIES`, `DisableBlocked`), puerto `shared/module_extensions.py` (capacidades, guardas, ganchos), adaptador `SharedModuleExtensions` (`infrastructure/django/gate.py`), casos de uso con extensiones (`application/use_cases.py`), repositorio `enabled_at()`, serializer y 409 ampliados (`api/`). Frontend: modelo/servicio con campos nuevos, lista de módulos (capacidades, adopción, motivos de bloqueo), diálogo (adopción y bloqueos), menú `routes.json` + i18n es/en/de y rutas `production/*`, `costing/*` (placeholders y Configuración). Docs: nota en `ddd.md`, `modulos-implementados.md` §3.11, `design-system.md` §6.

**Cobertura.** AC-01/INV-07: dominio + `test_extensions`/`test_production_costing_api`; AC-02/INV-01/02: idem; AC-03: spec de sidebar y capacidad ausente; AC-04/INV-03/04: dominio, casos de uso y API (dependientes y `blockers`); AC-05/INV-05/06: casos de uso (adopción, gancho único, nueva fecha al rehabilitar, fallo del gancho); AC-06/UI-01..04: specs de `module-list`, diálogo, `sidebar-menu`, `sidebar`.

**Verificación propia (no es el Quality Gate).**
- Backend: `test_domain` + `test_extensions` (31 pruebas, sin BD) OK con el `.venv` del checkout principal y una `DATABASE_URL` ficticia. **No se ejecutaron las pruebas con BD** (`test_api`, `test_production_costing_api` y el resto de la suite): el `.env` no se pudo copiar al worktree (denegado por política de credenciales). Tampoco se corrió `makemigrations --check` (no hay modelos nuevos).
- Frontend: Karma acotado (settings + core + sidebar) 121/121 OK con `app.component.spec.ts` apartado temporalmente (roto en `main`, restaurado sin cambios); `ng lint` OK. `node_modules` por enlace al checkout principal. Revisión visual: no verificada.

**Desviaciones respecto al plan.** Las pruebas de API de PB-MOD-005 viven en `test_production_costing_api.py` (archivo nuevo) en vez de en `test_api.py`; `test_api.py` solo se ajustó al catálogo y a la forma nueva. La excepción del gancho de adopción se propaga como 500 controlado por la transacción (sin manejo propio). No se creó prueba de `test_guards` nueva: el existente ya valida claves contra el catálogo y no hay vistas de negocio nuevas.

**Deuda técnica.** Las guardas de órdenes abiertas/costos sin cerrar y la capacidad `inventory.valuation` las registrarán Producción, Costeo e Inventario en sus historias; hasta entonces Costeo no es habilitable. `app.component.spec.ts` roto en `main` (preexistente). El diálogo de desactivación sigue sin validar datos existentes más allá de las guardas (PB-MOD-004).

**UI.** Pantalla de referencia: Configuración › Módulos existente (DDR vigente) y `module-settings`/`ComingSoon` para destinos; sin componentes compartidos nuevos.

## Review
**Quality Gate (subagente aislado, 2026-10-30): PASS CONDICIONADO — no es PASS pleno.** Sin hallazgos Critical/High ni pruebas fallando.

Ejecutado: backend sin BD `test_domain` + `test_extensions` + `test_settings_domain` 40/40 OK; `makemigrations --check` sin cambios; `bandit` sin hallazgos; Karma acotado (settings, core, sidebar) 121/121 OK (cobertura de líneas 56,1 % de lo ejecutado); `ng lint` OK; `ng build` OK.

**No realizado:** pruebas de backend con BD (`test_api`, `test_production_costing_api`, enforcement, guards, resto de la suite; no hay `.env`/BD en el entorno, revisadas solo por lectura y se estiman coherentes); `npm audit` (sin lockfile); revisión visual en navegador (no verificada).

Hallazgos abiertos: REV-01 (Medium, IMPLEMENTATION): falta la prueba 403 `module_disabled` de `production`/`costing` prevista en AC-03 y no consta como desviación; REV-02 (Low): carrera al habilitar Costeo podría ejecutar el gancho dos veces; REV-03 (Low): el diálogo decide la adopción por `key === 'costing'` y muestra la fecha del cliente.

**Condición para PASS pleno:** ejecutar la suite de backend con BD y resolver o documentar REV-01. La etapa se mantiene en REVIEW.

## Publicación
_Pendiente_
