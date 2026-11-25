# PLAN-2026-11-25-crm-tareas-actividad-comercial (v3)

**Task:** TASK-crm-tareas-actividad-comercial · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-crm-tareas-actividad-comercial-por-contactar-y-actividad / Ninguno

## Objective
Que el vendedor vea a quién debe contactar (tareas por responsable, vencimiento y estado) y registre qué pasó (actividad con canal y resultado) sobre clientes y oportunidades.

## Context
Resumen en `docs/tasks/TASK-crm-tareas-actividad-comercial.md`. Base: rama `crm` (incluye PB-CRM-003 y PB-CRM-004).

# Specification

## Domain context
Bounded context `crm`. Usa `customers` (cliente existente y activo) solo por `CustomerGateway`, y `shared.identity` (responsable) por `UserDirectory`. Ventas no interviene.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Tarea (`CRMTask`) | Próxima acción con vencimiento, responsable y estado | Tarjeta Trello |
| Actividad (`CRMActivity`) | Registro inmutable de lo ocurrido (canal, resultado, notas) | Tarjeta Trello |
| Relacionado | Exactamente un cliente **o** una oportunidad | Tarjeta Trello |
| Vencida | Tarea pendiente con `due_at` anterior a ahora; se calcula, no es estado | Decisión de diseño |

## Current behavior
No hay tareas ni actividad. `OpportunityModel.next_action_at` es solo una fecha (`infrastructure/django/models.py:74`).

## Expected behavior
Se crean, editan y gestionan tareas; se registran actividades; ambas se consultan por entidad y la lista «Por contactar» ordena por vencimiento.

## Domain rules / invariants
- **INV-01** Tarea y actividad pertenecen a una empresa y se relacionan con exactamente uno de `customer_id` / `opportunity_id` de **esa** empresa (CHECK de BD y validación).
- **INV-02** Estados de tarea: `pending`, `done`, `cancelled`, `archived`. Transiciones por métodos del agregado: `complete()` y `cancel()` desde pendiente; `reopen()` desde hecha/cancelada (borra `completed_at`); `archive()` desde hecha/cancelada (terminal). Cualquier otra transición → 409.
- **INV-03** `completed_at` se fija solo al completar; es nulo en pendiente y cancelada. Al archivar una tarea hecha se conserva (queda como registro de cuándo se completó); una archivada desde cancelada lo tiene nulo.
- **INV-04** Solo una tarea pendiente se edita (título, vencimiento, responsable); el relacionado no cambia.
- **INV-05** Título obligatorio, máx. 150 caracteres. `due_at` obligatorio. Responsable = usuario de la empresa (por defecto quien crea).
- **INV-06** Actividad: canal ∈ {`call`, `whatsapp`, `email`, `visit`, `other`}; resultado opcional ∈ {`contacted`, `no_answer`, `interested`, `not_interested`, `follow_up`}; notas ≤ 2000; se exige resultado **o** notas; `occurred_at` por defecto ahora y no futuro. Inmutable (sin editar ni borrar).
- **INV-07** No se crean tareas ni actividades para un cliente inactivo ni para una oportunidad cerrada con tarea nueva (la actividad sobre oportunidad cerrada **sí** se permite: es historial). Las tareas pendientes de una oportunidad cerrada siguen gestionables.
- **INV-08** Las archivadas no aparecen en ninguna lista ni en el historial de tareas.

## Acceptance criteria
- **AC-01** Crear tarea con título, vencimiento y relacionado (cliente u oportunidad); responsable por defecto = actor; queda `pending`.
- **AC-02** Rechazar relacionado ausente, doble o ajeno a la empresa (404 sin distinguir inexistente de ajeno); cliente inactivo → 409.
- **AC-03** Completar una tarea pendiente fija `completed_at` y estado `done`; completar otra vez → 409. Opcionalmente, en la misma transacción, crea una actividad con el mismo relacionado y vínculo a la tarea.
- **AC-04** Cancelar, reabrir y archivar siguen INV-02; archivar la oculta de todas las listas.
- **AC-05** Listar tareas con filtros `owner_id`, `status` (`pending`, `done`, `cancelled`, `overdue`, `all` — nunca incluye archivadas), `customer_id`, `opportunity_id`; orden por vencimiento ascendente; paginado; `overdue` calculado con el reloj del servidor.
- **AC-06** Editar tarea pendiente; editar una no pendiente → 409.
- **AC-07** Registrar actividad persistente e inmutable sobre cliente u oportunidad; listarla por entidad (más reciente primero); rechazar sin resultado ni notas, canal/resultado inválido o fecha futura.
- **AC-08** Aislamiento: ninguna operación ve ni toca datos de otra empresa; sin módulo `customers` habilitado → 403.
- **AC-09** Pantalla «Por contactar» con filtros Responsable/Estado, acciones por estado y estados de carga/vacío/error (UI-01..UI-03).
- **AC-10** Accesos desde la tarjeta del Kanban y la lista de clientes para «Registrar actividad», «Nueva tarea» e «Historial de actividad» (UI-04).

## Edge cases / Error cases
Responsable inexistente o de otra empresa → 400. Reabrir una tarea cuya oportunidad se cerró: permitido. Doble clic en «Completar» → un único cambio (bloqueo de fila). Vencimiento pasado al crear: permitido (queda vencida).

## Authorization / permissions
Mismo esquema que el resto de CRM: usuario autenticado de una empresa y `required_modules = ('customers',)`; empresa siempre desde `shared/tenancy.py`, nunca del cliente.

## API contract
Bajo `/api/crm/` (nuevo, sin romper nada existente):
- **API-01** `GET|POST /tasks/` — lista (filtros AC-05) y alta (`title`, `due_at`, `customer_id` | `opportunity_id`, `owner_id?`).
- **API-02** `GET|PATCH /tasks/<id>/` — detalle y edición (INV-04).
- **API-03** `POST /tasks/<id>/complete/` (cuerpo opcional `{activity: {channel, outcome?, notes?, occurred_at?}}`), `/cancel/`, `/reopen/`, `/archive/`.
- **API-04** `GET|POST /activities/` — `GET` exige `customer_id` u `opportunity_id`; `POST` crea (INV-06).
Respuestas incluyen nombres de relacionado y responsable, `is_overdue` y `completed_at`. Errores: 400 validación, 404, 409 `{detail, code}`.

## UI behavior
- **UI-01** Lista «Por contactar» según DDR (plantilla Lista §5, variante compacta bajo `lg`).
- **UI-02** Diálogos Tarea y Completar (actividad opcional), Reactive Forms.
- **UI-03** Estados: cargando, vacío, sin resultados, error con reintento, 400 por campo, 409 con aviso y recarga.
- **UI-04** Diálogo Actividad con historial y acciones en tarjeta del Kanban y fila de clientes.

## Non-functional requirements
Textos en `assets/i18n/{es,en,pt}.json`; índices por `(company_id, owner_id, status, due_at)`; sin dependencias nuevas.

## Out of scope
Ficha 360° (PB-CRM-002), WhatsApp (006), segmentos y `source_segment_id` (008/013/014), recordatorios/notificaciones, calendario, edición o borrado de actividad, Playwright.

## Open questions
Ninguna que bloquee. Supuestos registrados en el TASK (transiciones, `due_at` obligatorio).

# Test Specification

## Unit tests
Dominio de tarea (INV-02..INV-05 y transiciones inválidas) y actividad (INV-06), sin Django.

## Integration tests
API con PostgreSQL: crear/listar/filtrar, completar con y sin actividad (atómico), cancelar/reabrir/archivar, vencimiento con reloj fijo, aislamiento entre empresas, módulo deshabilitado, persistencia e inmutabilidad de actividad.

## E2E
**NO** — sin Playwright en el repo y sin dependencia nueva autorizada; la interfaz se verifica con pruebas Karma de componentes y servicios (mismo criterio que PB-CRM-003/004). Si el usuario quiere Playwright, es dependencia nueva y requiere su confirmación.

## Regression tests
Suite existente de `crm` (tableros, prospectos, oportunidades) sin cambios.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01, AC-02 | Unit dominio + API crear/validar/ajeno |
| AC-03 | API completar con/sin actividad, doble completar |
| AC-04 | Unit transiciones + API cancelar/reabrir/archivar |
| AC-05 | API listado con filtros, orden, vencidas (reloj fijo), exclusión de archivadas |
| AC-06 | API editar pendiente / no pendiente |
| AC-07 | Unit + API actividad (persistencia, inmutabilidad, validaciones) |
| AC-08 | API aislamiento y módulo deshabilitado |
| AC-09 | Karma componente lista, diálogos y servicio |
| AC-10 | Karma tarjeta Kanban y lista de clientes |

# Implementation Plan

## Architecture considerations
Se sigue el patrón de oportunidades: dominio puro (`domain/task.py`, `domain/activity.py`), servicios en `application/`, repositorios `Django…Repository(company_id)`, vistas finas con `run()`. Relacionado como dos columnas UUID anulables con CHECK de «exactamente una» (sin FK entre contextos para cliente; FK a `OpportunityModel` dentro de `crm`).

## Files/components affected
- Backend (`backend/modules/crm/`): `domain/{task,activity}.py`; `application/{task_services,activity_services}.py` ; `infrastructure/django/{models,repositories}.py`; `api/{task,activity}_{serializers,views,urls}.py` y `api/urls.py`; migración `0003_tasks_activities.py`; `tests/test_domain_task.py`, `test_api_tasks.py` (incluye las pruebas de actividad), `test_concurrency_tasks.py`.
- Frontend (`features/crm/`): `models/{task,activity}.ts`; `services/crm-tasks-api.service.ts`, `crm-activities-api.service.ts`; `pages/crm-task-list`; `components/{task-dialog,complete-task-dialog,activity-dialog,activity-fields,confirm-task-action-dialog}`; cambios en `crm-opportunity-board` y `crm-customer-list`; `crm.routes.ts`, app routes, `assets/data/routes.json`, `assets/i18n/{es,en,pt}.json`, `testing/crm-fixtures.ts` y specs.
- Docs: TASK, DDR, PLAN.

## Implementation steps
1. Dominio de tarea y actividad con pruebas unitarias (INV-02..INV-06).
2. Modelos, migración 0003 y repositorios (INV-01, INV-03; índices).
3. Servicios de aplicación (crear/editar/transiciones/completar con actividad/listar) usando `CustomerGateway`, `UserDirectory`, `Clock` (AC-01..AC-07).
4. API, serializers y rutas; pruebas de integración (AC-01..AC-08, API-01..API-04).
5. Modelos y servicios de Angular con pruebas (AC-09).
6. Página «Por contactar», diálogos y entrada de menú; i18n es/en/pt (AC-09, UI-01..UI-03).
7. Acciones en tarjeta del Kanban y lista de clientes; historial de actividad (AC-10, UI-04).
8. Lint (`ruff`, `flake8`, `npm run lint`, `i18n:check`), suites completas y revisión visual.

## Database / migrations
Migración nueva `0003_tasks_activities` (tablas `crm_task`, `crm_activity`); no se edita ninguna migración aplicada. Reversible (solo crea tablas).

## Risks
Ficha 360° aún ausente (se mitiga con componentes reutilizables). Concurrencia en transiciones (`select_for_update`).

## New dependencies
Ninguna.

## Changelog
- **v2** (2026-11-25): [Implementation Plan] Se alinea el plan con lo construido tras el Quality Gate (REV-03, REV-05, REV-06, REV-07): historial de actividad embebido en `activity-dialog` (sin `activity-history`), pruebas de actividad dentro de `test_api_tasks.py` más `test_concurrency_tasks.py`, sin protocolos nuevos en `ports.py`, diálogo de confirmación al cancelar/archivar y «Nueva tarea» desde la lista solo con cliente (oportunidades desde su tarjeta). Solicitado por delivery-publish. La Specification no cambia (INV-03 sigue pendiente de decisión, REV-04).
- **v3** (2026-11-25): [Specification] INV-03 enmendada: `completed_at` se conserva al archivar una tarea hecha. Aprobado explícitamente por el usuario en el chat («Conservar fecha»). Cierra REV-04; el código y el CHECK de BD no cambian.
