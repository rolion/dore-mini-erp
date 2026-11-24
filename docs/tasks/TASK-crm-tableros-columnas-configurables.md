# TASK-crm-tableros-columnas-configurables: PB-CRM-003 · Tableros y columnas configurables

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** `task/TASK-crm-tableros-columnas-configurables` (base: `crm`)
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/121
**Fuente:** https://trello.com/c/wFFKjHkX/2-pb-crm-003-tableros-y-columnas-configurables

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-24 | (nuevo) → INVESTIGATION | Task creado desde tarjeta de Trello | delivery-start |
| 2026-11-24 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | Decisiones de negocio respondidas por el usuario; DDR y ADR escritos | delivery-start |
| 2026-11-24 | PLANNING → ENGINEERING | Plan v1 COMPLETO, Specification READY; PR abierto contra `crm` | delivery-start |

## Investigación

### Requerimiento
Insumo (tarjeta Trello PB-CRM-003, no Specification aprobada): *Como administrador, quiero configurar las etapas comerciales de mi empresa.* Crear tableros con etapas iniciales editables y preservar oportunidades al reorganizarlos. UI: Seguimiento comercial → Tablero; selector de tablero y editor para crear, renombrar, ordenar y archivar etapas; si una etapa tiene tarjetas, pedir una etapa destino. Backend: `CRMBoard` (company_id, name, is_active) y `CRMStage` (board_id, name, position, is_active); reordenar y reasignar en una transacción. Tests: API (permisos, orden persistente, archivo con migración e IDs ajenos) y Playwright (editar etapas y recargar). No depende de otras tarjetas CRM; habilita PB-CRM-004 (Prospectos y oportunidades).

Aclaraciones del usuario: «usa la rama crm» (base y destino del PR). Respuestas: el tablero automático «Ventas» y los tableros nuevos **nacen sin etapas**; toda empresa recibe un tablero «Ventas» al registrarse y el admin puede crear más; Karma en lugar de Playwright.

### Hechos encontrados
- `origin/crm` apunta al mismo commit que `main` (`913b5286`). El PR 120 (`TASK-crm-listado-clientes`, base `crm`) crea el contexto `backend/modules/crm/` **de solo lectura** (sin modelos) y el submenú CRM; esta tarea añade la **primera persistencia** de `crm`.
- No existe `backend/modules/crm` en `main`; no existen oportunidades/tarjetas (las crea PB-CRM-004).
- `backend/modules/accounts/models.py:32-33` — único rol `admin`; `config/permissions.py:19` y `accounts/api/permissions.py:12-21`: el permiso por defecto de toda la API ya exige usuario admin de empresa activa.
- `backend/modules/service_catalog/api/views.py:20-37,45-80` y `service_catalog/infrastructure/django/` — patrón de referencia: vistas DRF con `required_modules`, `company_id_from(request)`, repositorio por empresa, `transaction.atomic`, paginador con validación.
- `backend/modules/modularity/domain/modules.py:20-45` — catálogo de módulos; no hay clave `crm` (el ADR del PR 120 la pospone; aquí se mantiene `required_modules = ('customers',)`).
- `shared/company_defaults/snapshot.json` (secciones `accounting, expenses, accounting_posting, purchases, inventory, modularity`) y `modules/inventory/infrastructure/defaults.py:1-45` — patrón de sección por empresa (`export`/`apply`/`register`, idempotente por nombre).
- `frontend/panel_admin/src/app/app.routes.ts:195-225` — rutas con `moduleGuard` + `data.module`; `assets/data/routes.json:40-62` — menú con `module`. Referencia de pantalla de configuración con diálogo: `features/inventory/pages/inventory-configuration` (`docs/design/design-system.md` §5). `@angular/cdk` ya está en `package.json:16`.
- No hay Playwright (solo Karma) en `frontend/panel_admin`.
- `docs/architecture/ddd.md:819-821` — dependencias entre módulos solo por fachada `services.py`.

### Hipótesis / supuestos no confirmados
- «Tarjeta» = futura oportunidad de PB-CRM-004; hoy no hay datos que reasignar. Se diseña un puerto de tarjetas con adaptador nulo (0 tarjetas) que PB-CRM-004 reemplaza. Registrado en el PLAN.
- Archivar un tablero con tarjetas se bloquea (409) en lugar de pedir destino: el tablero entero no tiene una «etapa destino» natural. Registrado en el PLAN.

### Módulos y dependencias relacionadas
`crm` (nuevo con modelos), `modularity` (solo `required_modules`), `shared.company_defaults`; futuro: PB-CRM-004 implementa el puerto de tarjetas.

### Implementaciones similares existentes
`service_catalog` (CRUD por empresa con repositorio/casos de uso), `inventory/infrastructure/defaults.py` (defaults por empresa), `inventory-configuration` (editor con diálogo).

### Comportamiento actual
No existe ningún concepto de tablero ni etapa comercial en backend, frontend ni docs (grep `crm|tablero|stage`).

### Restricciones
Aislamiento por `company_id` (repositorio por empresa, IDs ajenos → 404); nunca editar migraciones aplicadas; sin dependencias nuevas; textos i18n es/en/pt; reordenar y reasignar en una transacción; `crm` no importa `accounts`.

### Riesgos identificados
- Conflicto de merge con PR 120 (`INSTALLED_APPS`, `config/urls.py`, `routes.json`, `app.routes.ts`, i18n, `crm/` skeleton): quien entre segundo rebasa sobre `crm`; los cambios son aditivos.
- Carrera entre dos admins reordenando: se bloquea la fila del tablero (`select_for_update`) y se exige el conjunto completo de etapas activas.
- Sin tarjetas reales no se puede probar la reasignación de extremo a extremo hasta PB-CRM-004: se prueba con un puerto falso y se deja contrato documentado.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — primera persistencia del contexto `crm`, migración nueva, contrato API nuevo y un puerto hacia datos de un contexto futuro (tarjetas) que debe ser transaccional con el archivo de etapas.

### Diseño requerido
**SI** — pantalla nueva con editor de etapas, reordenamiento y diálogo de reasignación.

## Diseño
`docs/design/DDR-crm-tableros-columnas-configurables-editor-de-etapas.md`

## Arquitectura
`docs/adr/ADR-crm-tableros-columnas-configurables-modelo-y-puerto-de-tarjetas.md`

## Plan
`docs/plans/PLAN-2026-11-24-crm-tableros-columnas-configurables.md` (v1, COMPLETO, READY)

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
