# PLAN-2026-11-24-crm-prospectos-oportunidades (v1)

**Task:** TASK-crm-prospectos-oportunidades · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** `docs/design/DDR-crm-prospectos-oportunidades-kanban-y-prospectos.md` · `docs/adr/ADR-crm-prospectos-oportunidades-modelo-conversion-y-vinculos.md`

## Objective
Permitir que el vendedor registre prospectos, cree oportunidades en un tablero, las mueva entre etapas, las cierre como ganadas o perdidas (con vínculo opcional a un pedido) y convierta prospectos en clientes sin duplicar, con historial de cambios de etapa.

## Context
Historia PB-CRM-004 (Trello, ver TASK). Decisiones del usuario: base `crm`; conversión vincula al cliente existente por teléfono; perdida exige motivo; pedido del mismo cliente, no cancelado, uno a uno; responsable = usuario de la empresa, moneda `BOB`; Karma en lugar de Playwright. Depende de PB-CRM-003 (ya en `crm`).

# Specification

## Domain context
Bounded context `crm`. Relacionados (solo por fachada `services.py` desde `infrastructure/adapters.py`): `customers`, `sales`, `inventory` (ya usado), `shared.identity`, `shared.module_gate`.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Prospecto (`Lead`) | Persona interesada que aún no es cliente | tarjeta Trello |
| Oportunidad (`Opportunity`) | Posible venta ubicada en una etapa de un tablero; es la «tarjeta» | tarjeta / PB-CRM-003 |
| Convertir | Enlazar el prospecto a un cliente (existente o recién creado) | tarjeta + usuario |
| Cerrar | Marcar la oportunidad como ganada o perdida | tarjeta |
| Siguiente acción | Fecha/hora (`next_action_at`) de la próxima gestión | tarjeta |
| Responsable | Usuario de la empresa dueño de la oportunidad (`owner_id`) | tarjeta + usuario |

## Current behavior
Sin prospectos ni oportunidades; `card_count` de tableros siempre 0 (`NoCards`, `crm/infrastructure/adapters.py:77-84`, usado en `crm/api/board_views.py:15-18`). Ver TASK.

## Expected behavior
El vendedor crea prospectos y oportunidades (para un prospecto o un cliente) en la primera etapa activa o en la etapa elegida, las mueve dentro de su tablero, filtra por responsable y prospecto/cliente, cierra como ganada (opcionalmente con pedido) o perdida (con motivo) y convierte prospectos en clientes sin crear duplicados. Cada cambio de etapa queda registrado. Archivar etapas/tableros respeta las oportunidades abiertas.

## Domain rules / invariants
- INV-01 (nueva): una oportunidad tiene prospecto, cliente o ambos; toda referencia pertenece a la misma empresa (ids ajenos → 404).
- INV-02 (nueva): solo oportunidades **abiertas** se mueven/editan; el destino es una etapa **activa del mismo tablero** de la oportunidad.
- INV-03 (nueva): `won`/`lost` fijan `closed_at`; `lost` exige `lost_reason` (1-500); `open` no tiene `closed_at`, `order_id` ni motivo. Cerrar es idempotente con el mismo resultado; otro resultado → 409.
- INV-04 (nueva): un prospecto convertido apunta a un único cliente; convertir de nuevo devuelve el mismo cliente sin cambios ni clientes nuevos.
- INV-05 (nueva): conversión: cliente activo elegido o único coincidente por teléfono normalizado (misma normalización que Clientes); varios coincidentes sin elección → 409; ninguno → se crea el cliente. Las oportunidades abiertas del prospecto reciben `customer_id`.
- INV-06 (nueva): vínculo a pedido: pedido de la empresa, del mismo cliente que la oportunidad (que debe tenerlo), no cancelado, no vinculado a otra oportunidad; solo en oportunidades ganadas.
- INV-07 (nueva): `amount` ≥ 0 en `Decimal(12,2)`, `currency = 'BOB'`; `owner_id` debe ser usuario de la empresa (por defecto, quien crea).
- INV-08 (nueva): todo cambio de etapa (alta, mover, reasignación por archivo de etapa) escribe un registro `StageChange` inmutable.
- INV-09 (existente de PB-CRM-003): `card_count` y reasignación al archivar una etapa cuentan/mueven oportunidades **abiertas**; un tablero con oportunidades abiertas no se archiva.
- INV-10 (existente): todo dato se filtra por `company_id` del usuario autenticado.

## Acceptance criteria
- AC-01: crear un prospecto con teléfono lo guarda con `normalized_phone`; nombre obligatorio; se puede editar y listar con búsqueda por nombre/teléfono/email y filtro convertido/no.
- AC-02: crear una oportunidad para un prospecto o un cliente de la empresa (uno de los dos o ambos), con título, importe, siguiente acción opcional y responsable; queda en la primera etapa activa del tablero (o la indicada) y registra su `StageChange` inicial. Tablero sin etapas activas → 409 `board_has_no_stages`.
- AC-03: mover a una etapa activa del mismo tablero actualiza la etapa y registra `StageChange`; etapa de otro tablero/archivada → 400; etapa o tablero de otra empresa → 404; oportunidad cerrada → 409.
- AC-04: cerrar perdida sin motivo → 400; con motivo cierra con `closed_at`. Cerrar ganada sin requisitos funciona. Repetir el mismo cierre → 200 sin cambiar `closed_at`; resultado distinto → 409 `already_closed`.
- AC-05: convertir un prospecto crea un cliente (sin coincidencias), vincula al único coincidente por teléfono, o responde 409 `multiple_customer_matches` con candidatos; con `customer_id` válido vincula a ese. Repetir la conversión devuelve el mismo cliente (200) sin crear otro. Las oportunidades abiertas del prospecto pasan a tener `customer_id`.
- AC-06: vincular un pedido (al cerrar ganada o luego) solo si es del mismo cliente, no cancelado y no usado por otra oportunidad; si no, 409 con código (`customer_required`, `order_customer_mismatch`, `order_cancelled`, `order_already_linked`, `sales_disabled`); pedido o cliente de otra empresa → 404.
- AC-07: filtros del listado de oportunidades por `board_id` (obligatorio), `owner_id`, `lead_id`, `customer_id`, `status`; los ids ajenos devuelven 404 / lista vacía sin filtrar datos de otra empresa.
- AC-08: `card_count` de tableros cuenta oportunidades abiertas; archivar una etapa con oportunidades exige destino y las reasigna con `StageChange`; un tablero con oportunidades abiertas no se archiva (409).
- AC-09: 403 sin empresa/no admin, 401 sin sesión, módulo `customers` deshabilitado → respuesta de módulo no habilitado; el responsable debe ser de la empresa (400).
- AC-10: UI **Oportunidades**: tablero Kanban con selector de tablero, filtros por responsable y prospecto/cliente, tarjeta con contacto, importe y siguiente acción, «Mover a…», diálogos de oportunidad, cierre (ganada con selector de pedido; perdida con motivo) y conversión; estados cargando/vacío/error/409.
- AC-11: UI **Prospectos**: lista con búsqueda y paginación, alta/edición y «Convertir en cliente».

## Edge cases / Error cases
Prospecto sin teléfono (se crea cliente sin teléfono); teléfono no normalizable (se compara el texto recortado, como Clientes); doble clic en convertir/cerrar; dos usuarios cerrando a la vez (bloqueo de fila); oportunidad ganada de un prospecto sin convertir que quiere pedido (409 `customer_required`, la UI ofrece convertir); pedido cancelado después de vincular (la referencia permanece); archivar la última etapa con oportunidades abiertas sin destino (409); amount negativo o con más de 2 decimales (400).

## Authorization / permissions
Único rol `admin` ya exigido por el permiso por defecto; `required_modules = ('customers',)`; la empresa sale de `company_id_from(request)`; el selector de pedidos exige además Ventas habilitado (`module_gate`).

## API contract
Base `/api/crm/`. Nuevo; los endpoints de `boards/` solo cambian en que `card_count` es real. Errores: `{campo: [mensajes]}` (400), `{detail, code, ...}` (409), 404 para ids ajenos.
- API-01 `GET /leads/?search=&converted=true|false&page=&page_size=` → paginado `[{id, name, phone, normalized_phone, email, converted_customer_id, created_at}]`. `POST /leads/` `{name, phone?, email?}` → 201. `GET/PATCH /leads/<id>/` (`name, phone, email`).
- API-02 `POST /leads/<id>/convert/` `{customer_id?}` → 200 `{lead, customer: {id, name, phone}, created: bool}` (idempotente) · 409 `multiple_customer_matches` `{candidates: [{id, name, phone}]}`.
- API-03 `GET /opportunities/?board_id=&owner_id=&lead_id=&customer_id=&status=open|won|lost&page=&page_size=` → paginado de `[{id, board_id, stage_id, lead: {id, name, phone}|null, customer: {id, name, phone}|null, title, owner: {id, name}, amount, currency, next_action_at, status, closed_at, order_id, lost_reason, created_at}]`. `POST /opportunities/` `{board_id, stage_id?, lead_id?|customer_id?, title, amount, next_action_at?, owner_id?}` → 201.
- API-04 `GET/PATCH /opportunities/<id>/` (`title, amount, next_action_at, owner_id`, abierta); `POST /opportunities/<id>/move/` `{stage_id}`; `POST /opportunities/<id>/close/` `{result, lost_reason?, order_id?}`; `PUT /opportunities/<id>/order/` `{order_id}` (ganada); `GET /opportunities/<id>/orders/` pedidos vinculables del cliente `[{id, order_date, total, status}]`; `GET /opportunities/<id>/history/` → `[{from_stage_id, to_stage_id, changed_by, changed_at}]`.
- Compatibilidad: sin cambios incompatibles; `card_count` pasa de 0 a real.

## UI behavior
- UI-01: menú CRM con **Oportunidades** y **Prospectos** (`/pocketbiz/crm/opportunities`, `/pocketbiz/crm/leads`), `moduleGuard` de `customers`.
- UI-02: Kanban según DDR y la plantilla nueva en `design-system.md` §5: columnas por etapa activa, tarjetas con contacto/importe/siguiente acción, filtros, estados vacío/cargando/error/409.
- UI-03: «Mover a…» accesible (teclado/móvil), guardado inmediato y recarga desde el servidor.
- UI-04: diálogo de cierre (ganada: pedido opcional; perdida: motivo obligatorio) con el patrón de acción irreversible; diálogo de conversión con elección ante varios coincidentes.
- UI-05: lista de prospectos con plantilla Lista y variante compacta; todo texto por claves i18n es/en/pt; botones de icono con `title`/`aria-label`.

## Non-functional requirements
Escrituras atómicas con bloqueo de fila (prospecto en conversión, oportunidad en cierre/mover); consultas sin N+1 (resolver contactos y responsables por lote por página); índices en `(company_id)`, `(board, stage, status)`, `owner_id`; accesible por teclado.

## Out of scope
Tareas y actividad (PB-CRM-005), WhatsApp (006/012), segmentos, arrastrar y soltar, reabrir cerradas, ordenamiento manual dentro de columna, detalle de oportunidad con actividad, sincronización posterior con el pedido, multi-moneda, importación de prospectos, Playwright.

## Open questions
- Ninguna que bloquee. Pendiente futuro: texto de «siguiente acción» (lo cubrirá PB-CRM-005).

# Test Specification

## Unit tests
Dominio puro (`crm/tests/test_domain_opportunity.py`): INV-01…INV-04, INV-07 (mover solo abiertas y mismo tablero, cierre idempotente y motivo, conversión una sola vez, importes).

## Integration tests
API (`crm/tests/test_api_leads.py`, `test_api_opportunities.py`) con `APITestCase`, dos empresas: AC-01…AC-09 incluyendo conversión (crea / vincula único / varios / `customer_id` / idempotente / concurrencia simulada), cierre idempotente, vínculo a pedido con cada código de error (crea pedidos con fachadas de Ventas), aislamiento entre empresas, historial de etapas, `card_count` y archivo de etapa con reasignación real (`DjangoStageCards`). Flujo completo «consulta → venta ganada → pedido» a nivel API. Fronteras: `test_boundaries.py` actualizado; `makemigrations --check`; fachadas nuevas de `customers`/`sales` con pruebas propias.
Frontend (Karma): servicios API (URLs/cuerpos), páginas `crm-opportunity-board` y `crm-lead-list`, diálogos (oportunidad, cierre, conversión), menú, paridad y uso de claves i18n.

## E2E
**NO** — la tarjeta pide Playwright, pero no está instalado en el repo (dependencia nueva) y el usuario ya eligió Karma en PB-CRM-003; el flujo consulta → ganada → pedido se cubre con una prueba de integración de API de punta a punta y con pruebas de componente.

## Regression tests
Suites de `crm` (boards), `customers`, `sales`, `company_defaults`; `npm run i18n:check`, `npm run lint`.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | API leads + dominio |
| AC-02 | API opportunities (crear, sin etapas, historial) |
| AC-03 | API move (mismo tablero, otra empresa, cerrada) + dominio |
| AC-04 | API close (motivo, idempotencia, 409) + dominio |
| AC-05 | API convert (4 caminos + idempotencia) + fachadas customers |
| AC-06 | API order link (cada código) + fachadas sales |
| AC-07 | API filtros y aislamiento |
| AC-08 | API boards con `DjangoStageCards` real |
| AC-09 | API permisos/módulo/responsable |
| AC-10 | Karma `crm-opportunity-board`, diálogos, servicio |
| AC-11 | Karma `crm-lead-list`, servicio |

# Implementation Plan

## Architecture considerations
Ver ADR: dominio puro (`Lead`, `Opportunity`), casos de uso en `application/`, puertos (`CustomerGateway`, `OrderGateway`, `UserDirectory`, `StageCards`) con adaptadores únicos en `infrastructure/adapters.py` que usan fachadas.

## Proposed solution
Nuevos agregados y repositorios por empresa; servicios `LeadService` y `OpportunityService` (el llamador abre la transacción; bloqueo de fila); vistas DRF finas; fachadas de lectura/creación en `customers` y `sales`; sustitución de `NoCards` por `DjangoStageCards`; dos pantallas Angular con servicios inyectables y Reactive Forms.

## Files/components affected
- Backend: `backend/modules/crm/` (`domain/{lead,opportunity}.py`, `application/{ports,lead_services,opportunity_services}.py`, `infrastructure/django/{models,repositories}.py`, `infrastructure/adapters.py`, `api/{lead,opportunity}_{serializers,views,urls}.py`, `api/urls.py`, `api/board_views.py`, `migrations/0002_*.py`, `tests/`), `backend/modules/customers/services.py` y `backend/modules/sales/services.py` (fachadas + pruebas), `modules/sales/tests/test_boundaries.py`, `docs/architecture/ddd.md`.
- Frontend: `features/crm/` (`crm.routes.ts`, `pages/{crm-opportunity-board,crm-lead-list}`, `components/{opportunity-dialog,lead-dialog,close-opportunity-dialog,convert-lead-dialog}`, `services/{crm-leads-api,crm-opportunities-api}.service.ts`, `models/`, `testing/`), `assets/data/routes.json`, `assets/i18n/{es,en,pt}.json`, `sidebar-menu.spec.ts`.
- Migraciones: `crm 0002` (tablas nuevas, restricciones únicas/check).
- Docs: `design-system.md` §5 (plantilla Kanban), `ddd.md`, TASK.

## Implementation steps
1. Dominio `Lead` y `Opportunity` + pruebas (INV-01…04, INV-07).
2. Modelos, migración `0002` y repositorios por empresa (INV-10, INV-08).
3. Fachadas `customers`/`sales`, puertos y adaptadores; `DjangoStageCards` (AC-05, AC-06, AC-08).
4. Casos de uso de prospectos y conversión (AC-01, AC-05).
5. Casos de uso de oportunidades: crear, editar, mover, cerrar, vincular pedido, historial (AC-02…AC-04, AC-06).
6. Serializers, vistas, URLs, filtros y paginación; errores 400/404/409 (AC-07, AC-09).
7. Pruebas de API, flujo completo, aislamiento y fronteras; `ruff`/`flake8` en lo cambiado.
8. Frontend: modelos, servicios, rutas, menú, i18n.
9. Pantallas y diálogos (UI-01…05) + specs Karma; `i18n:check`, `lint`, `npm test`.
10. Actualizar `ddd.md`, `design-system.md` y TASK.

## Database / migrations
`crm 0002`: crea `crm_lead`, `crm_opportunity`, `crm_stage_change` con CheckConstraints y unicidad condicional de `order_id`; sin tocar datos existentes. Nunca editar `0001`. Reversible con `migrate crm 0001`.

## Risks
Conversión/cierre concurrentes (bloqueo de fila + idempotencia); pedido vinculado en carrera (unicidad en BD); dependencias nuevas de `crm` hacia `customers`/`sales` (solo fachada); Kanban con muchas tarjetas (carga hasta 200 abiertas por tablero, filtros); alcance amplio en una sola tarea (se mitiga con pasos pequeños y pruebas por paso).

## New dependencies
Ninguna.
