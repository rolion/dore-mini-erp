# TASK-crm-tareas-actividad-comercial: PB-CRM-005 · Tareas y actividad comercial

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** SI
**Rama:** `task/TASK-crm-tareas-actividad-comercial` (base: `crm`)
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/123
**Fuente:** https://trello.com/c/UjJ6EBn7/1-pb-crm-005-tareas-y-actividad-comercial

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-25 | (nuevo) → INVESTIGATION | Task creado desde tarjeta de Trello | delivery-start |
| 2026-11-25 | INVESTIGATION → DESIGN → PLANNING | Decisiones de negocio respondidas por el usuario; DDR escrito | delivery-start |
| 2026-11-25 | PLANNING → ENGINEERING | Plan v1 COMPLETO, Specification READY | delivery-start |
| 2026-11-25 | ENGINEERING → REVIEW | Implementación completa según PLAN v1 | delivery-build |

## Investigación

### Requerimiento
Insumo (tarjeta Trello PB-CRM-005, no Specification aprobada): *Como vendedor, quiero ver a quién debo contactar y registrar qué pasó.* Crear notas, próximas acciones y resultados asociados a clientes u oportunidades. UI: «Seguimiento comercial → Por contactar»: lista por responsable, vencimiento y estado; formulario de actividad accesible desde la ficha y la tarjeta. Backend: `CRMTask` (company_id, customer_id u opportunity_id, owner_id, title, due_at, status, completed_at, source_segment_id opcional) y `CRMActivity` (actor_id, related_entity, channel, outcome, notes, occurred_at). Tests: API (completar tareas, vencimiento, acceso, persistencia de actividad) y Playwright (crear tarea, registrar resultado y verla en la ficha). Depende de PB-CRM-004 (ya integrado en `crm`); habilita PB-CRM-002, -006, -008, -013 y -014. Alcance de la dependencia: tareas y notas de clientes pueden avanzar antes de PB-CRM-004; esa historia habilita el vínculo desde oportunidades.

Aclaraciones del usuario: «usa la rama `crm`» (base y destino del PR; ya contiene PB-CRM-003 y PB-CRM-004). Respuestas de negocio (2026-11-25):
1. Estados de tarea: **Pendiente / Hecha / Cancelada / Archivada**; las **archivadas no se muestran**.
2. Canales de actividad: **Llamada, WhatsApp, Email, Visita, Otro**.
3. Resultados: **Contactado, Sin respuesta, Interesado, No interesado, Seguimiento pendiente**.
4. Al completar una tarea: **actividad opcional en el mismo diálogo**.
Por coherencia con PB-CRM-003/004 (decisión del usuario allí) y porque no hay Playwright instalado, la verificación de interfaz usa Karma.

### Hechos encontrados
- `backend/modules/crm/` ya existe con tablero, prospectos y oportunidades (`infrastructure/django/models.py:7-115`: `BoardModel`, `StageModel`, `LeadModel`, `OpportunityModel`, `StageChangeModel`; migraciones `0001`, `0002`).
- `backend/modules/crm/api/opportunity_views.py:25-42` — patrón vista fina + `opportunity_service(request)` con `company_id_from(request)`; `api/common.py:13-49` — `run`, `body`, `query_uuid`, `query_choice`, traducción a 400/404/409; `required_modules = ('customers',)`.
- `backend/modules/crm/application/ports.py:55-112` — puertos `CustomerGateway` (`get`, `get_many`), `UserDirectory` (`exists`, `names`, `search`) y `Clock`; adaptadores en `infrastructure/adapters.py` (único sitio que importa otros módulos).
- `backend/modules/crm/domain/errors.py:4-21` — `CrmValidationError`, `CrmNotFound`, `CrmConflict(code, message)`; `domain/opportunity.py` — limpieza de campos (`clean_title`, longitud 150) y estados por métodos del agregado.
- `backend/modules/crm/api/urls.py:5-10` — enrutado `api/crm/…`; `config/urls.py:28`.
- `backend/shared/identity.py:6-30` — `CompanyUserDirectory`; id de usuario entero (`BigIntegerField`).
- `frontend/panel_admin/src/app/features/crm/` — páginas `crm-opportunity-board`, `crm-lead-list`, `crm-customer-list`; diálogos `NgbModal` en `components/`; servicios `crm-*-api.service.ts` con `CrmApiError`; `testing/crm-fixtures.ts`; rutas en `crm.routes.ts`; menú CRM en `assets/data/routes.json:63-110`.
- `docs/design/design-system.md:117,152,224` — plantillas Lista, Kanban y «Diálogo de acción irreversible con motivo».
- La ficha 360° (PB-CRM-002) **no está** en `crm` (vive en otra rama paralela): no hay pantalla de ficha donde embeber todavía.
- No existe Playwright en el repo.

### Hipótesis / supuestos no confirmados
- `due_at` obligatorio (la lista se ordena por vencimiento); `source_segment_id` se **omite** (los segmentos llegan en PB-CRM-008/014, que añadirán la columna nullable por migración).
- Una tarea/actividad se asocia a **exactamente uno** de cliente u oportunidad (la oportunidad solo-prospecto cubre al prospecto sin cliente).
- Transiciones (decisión de criterio, cambiable): Pendiente→Hecha, Pendiente→Cancelada, Hecha/Cancelada→Pendiente (reabrir), Hecha/Cancelada→Archivada (terminal, oculta). Una pendiente no se archiva directamente.
- Actividad inmutable (solo se agrega); «vencida» = pendiente con `due_at` anterior a ahora (calculado, no es un estado).

### Módulos y dependencias relacionadas
`crm` (nuevas entidades), `customers` (validar cliente por `CustomerGateway`), `shared.identity` (responsables). Sin cambios en otros módulos.

### Implementaciones similares existentes
`crm` oportunidades (dominio + servicio + repositorio por empresa + vistas finas), `features/crm/pages/crm-lead-list` (lista con filtros, paginación y diálogos), `crm/components/close-opportunity-dialog` (diálogo con motivo).

### Comportamiento actual
No hay tareas ni actividad comercial. Las oportunidades tienen solo `next_action_at` sin texto.

### Restricciones
`CLAUDE.md`: aislamiento por `company_id`, dominio sin Django, módulos solo por fachada, sin texto hardcodeado (i18n es/en/pt), Reactive Forms, nunca editar migraciones aplicadas, sin dependencias nuevas.

### Riesgos identificados
- Dependencia de PB-CRM-002 para la ficha: se entregan componentes reutilizables y accesos desde tarjeta y lista de clientes; la ficha los embeberá.
- Concurrencia al completar/reabrir: bloquear fila (`select_for_update`) como en oportunidades.

### Veredicto de complejidad
**NEEDS_PLAN** — dos entidades nuevas dentro de un contexto existente, siguiendo patrones ya probados; sin módulo nuevo ni decisión arquitectónica. Plan COMPLETO por transiciones de estado y contrato API nuevo.

### Diseño requerido
**SI** — pantalla nueva «Por contactar» y diálogos de tarea/actividad.

## Diseño
Ver `docs/design/DDR-crm-tareas-actividad-comercial-por-contactar-y-actividad.md`.

## Arquitectura
No aplica según veredicto.

## Plan
`docs/plans/PLAN-2026-11-25-crm-tareas-actividad-comercial.md` (v1, COMPLETO). Specification readiness: READY.

## Implementación

**Backend (`backend/modules/crm/`)** — dominio puro `domain/task.py` y `domain/activity.py` (INV-01…INV-06); `application/{related,task_services,activity_services}.py`; modelos `TaskModel`/`ActivityModel` y migración `0003_tasks_activities`; repositorios `DjangoTaskRepository`/`DjangoActivityRepository` y `DjangoOpportunityRepository.get_many`; API `/api/crm/tasks/…` y `/api/crm/activities/` (API-01…API-04). Cubre AC-01…AC-08 con `tests/test_domain_task.py` y `tests/test_api_tasks.py` (suite `modules.crm`: 139 pruebas OK con PostgreSQL).

**Frontend (`features/crm/`)** — modelos y servicios (`crm-tasks-api`, `crm-activities-api`), página «Por contactar» (`crm-task-list`, ruta `/pocketbiz/crm/tasks`, ítem de menú), diálogos `task-dialog`, `complete-task-dialog`, `activity-dialog` (con historial) y `activity-fields` compartido; acciones «Actividad» y «Nueva tarea» en la tarjeta del Kanban y en la lista de clientes (AC-09, AC-10). i18n es/en/pt. Karma: 1952 pruebas OK; `npm run lint`, `i18n:check` y `ng build` sin errores.

**Pantalla de referencia seguida:** `crm-lead-list` (Lista) y `close-opportunity-dialog` (diálogos). Se reutilizaron `toLocalInput/fromLocalInput`, `CrmApiError`/`crmErrors`, badges `badge-outline` y botones del sistema; no se añadieron patrones nuevos (no se modificó `design-system.md`).

**Desviaciones respecto al plan (detalle de implementación, sin cambiar Specification):**
- `completed_at` se **conserva** al archivar una tarea hecha (INV-03 lo daba «nulo en los demás estados»); la restricción de BD permite `archived` con o sin fecha. No afecta ningún AC.
- No se añadieron protocolos de repositorio a `ports.py` (el módulo ya usa duck typing para sus repositorios).
- La lista «Por contactar» es una tabla Bootstrap apilada bajo `md` (CSS propio) en lugar de `ngx-datatable` + tarjetas; el DDR pedía «variante compacta» y esto la cubre con menos código.
- «Nueva tarea» desde la lista permite elegir **cliente**; para tareas de una oportunidad se usa el botón de su tarjeta del Kanban (el selector de oportunidades requeriría tablero).
- El «Historial de actividad» no es un botón aparte: va dentro del diálogo «Actividad».
- Se copió `backend/.env` (no versionado, sin leerlo) al worktree y se enlazó `node_modules` para poder ejecutar pruebas; ambos están ignorados por git.

**Deuda técnica:** sin Playwright (E2E NO, ver PLAN); la ficha 360° (PB-CRM-002) deberá embeber `activity-dialog`/`task-dialog`; no hay vista de calendario ni recordatorios (fuera de alcance).

## Review
_Pendiente_

## Publicación
_Pendiente_
