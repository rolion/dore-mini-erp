# PLAN-2026-11-27-crm-tableros-seguimiento-comercial (v1)

**Task:** TASK-crm-tableros-seguimiento-comercial · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** `docs/design/DDR-crm-tableros-seguimiento-comercial-lista-de-tableros-y-tablero.md` · Ninguno (ADR)

## Objective
Dar a CRM una entrada «Seguimiento comercial» donde se crean tableros (solo nombre, sin columnas), se agregan y archivan columnas y se registran tarjetas vinculadas a un cliente o prospecto, reutilizando tableros/etapas y oportunidades existentes.

## Context
Historia PB-CRM-006 (Trello, ver TASK). Decisiones del usuario: base `crm`; la tarjeta es la oportunidad; el bloqueo de archivo aplica solo a la nueva pantalla; entrada de menú nueva.

# Specification

## Domain context
Bounded context `crm`. Tablero/etapa (`Board`/`Stage`) y `Opportunity` ya existen; se amplía `Opportunity` con descripción y se relaja el importe.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Tablero | `Board` | PB-CRM-003 |
| Columna | `Stage` activa del tablero | tarjeta Trello |
| Tarjeta de seguimiento | `Opportunity` abierta en una columna | decisión del usuario |
| Archivar columna | `is_active=false` de la etapa | PB-CRM-003 |

## Current behavior
Ver TASK. API ya soporta crear tablero sin etapas, agregar etapa al final y archivar con 409 `stage_has_cards`; alta de oportunidad exige importe y no guarda descripción (`api/opportunity_serializers.py:14-23`, `domain/opportunity.py`).

## Expected behavior
Ver UI/API abajo. Una tarjeta nueva guarda nombre (`title`), contacto, descripción y queda en la columna de origen con importe 0 y responsable = usuario actual.

## Domain rules / invariants
- INV-01 (existente): nombres de tablero/columna únicos y 1-80 caracteres; columna nueva va al final.
- INV-02 (existente): una oportunidad pertenece a un cliente o prospecto de la misma empresa.
- INV-03 (nueva): la descripción es opcional, recortada, ≤ 1000 caracteres.
- INV-04 (nueva): el importe es opcional al crear; sin valor se guarda `0.00` (`Decimal`).
- INV-05 (existente): archivar columna con oportunidades abiertas sin destino → 409 `stage_has_cards`.

## Acceptance criteria
- AC-01: la lista «Seguimiento comercial» muestra cada tablero activo como tarjeta con su nombre; al elegirla abre su tablero.
- AC-02: «Crear nuevo tablero» pide solo nombre obligatorio; al guardar abre el tablero vacío (sin columnas) con «Agregar columna» disponible. Los tableros existentes conservan columnas y tarjetas.
- AC-03: «Agregar columna» exige nombre; la primera queda a la izquierda y las siguientes a la derecha; el orden persiste al recargar.
- AC-04: cada columna muestra nombre, botón de tres puntos con «Agregar tarjeta» y «Archivar columna», y sus tarjetas por nombre.
- AC-05: archivar una columna vacía la oculta; con tarjetas activas queda bloqueado con aviso de moverlas primero, sin cambios.
- AC-06: «Agregar tarjeta» exige Nombre y Cliente o prospecto; Descripción opcional; el selector ofrece solo clientes y prospectos de la empresa; la tarjeta aparece en la columna de origen y persiste al recargar. Crear sin importe funciona (0.00) y sin descripción también.
- AC-07: la descripción se devuelve en la API de oportunidades y se puede editar; Oportunidades (Kanban) sigue funcionando con importe y cierre.
- AC-08: aislamiento: tablero, columna o contacto de otra empresa → 404; no admin/sin empresa → 403; sin sesión → 401.

## Edge cases / Error cases
Nombre solo con espacios o duplicado (400); tablero sin columnas no permite «Agregar tarjeta»; tablero archivado (409/400); columna archivada por otra sesión (el 409 recarga); contacto eliminado/inactivo.

## Authorization / permissions
Admin de empresa activa; `required_modules = ('customers',)` como el resto de CRM.

## API contract
- API-01: `POST /api/crm/opportunities/` acepta `description` (opcional) y `amount` opcional (por defecto `"0.00"`); respuesta y `PATCH` incluyen `description`. Compatible hacia atrás.
- API-02: tableros/etapas sin cambios (se reutilizan `POST /boards/`, `POST /boards/<id>/stages/`, `POST /boards/<id>/stages/<id>/archive/` sin `target_stage_id`).

## UI behavior
- UI-01: menú «Seguimiento comercial» → `/pocketbiz/crm/tracking`; tablero en `/pocketbiz/crm/tracking/:boardId` (DDR; `design-system.md` §5 Kanban).
- UI-02: lista de tableros en rejilla de tarjetas + modal «Crear nuevo tablero» (nombre).
- UI-03: tablero con «Agregar columna», columnas con menú de tres puntos, tarjetas por nombre, estados vacío/cargando/error/409 (DDR).
- UI-04: diálogo «Agregar tarjeta» (Nombre, Cliente o prospecto, Descripción); aviso bloqueante al archivar columna con tarjetas.
- UI-05: todo texto con claves i18n es/en/pt; botones de icono con `title` y `aria-label`.

## Non-functional requirements
Sin N+1 (la lista de oportunidades por tablero ya es paginada); accesible por teclado (menú `ngbDropdown`).

## Out of scope
Tareas e historial en la tarjeta (PB-CRM-005), detalle/edición de tarjeta en la nueva pantalla, arrastrar entre columnas (ya existe en Oportunidades), renombrar/reordenar columnas (editor «Tablero»), quitar la reasignación del editor.

## Open questions
Ninguna.

# Test Specification

## Unit tests
Dominio (`crm/tests/test_domain_opportunity.py`): INV-03 e INV-04 (descripción recortada/limitada; importe omitido → 0.00).

## Integration tests
API (`test_api_opportunities.py`): AC-06/07/08 (alta sin importe, con descripción, edición de descripción, otra empresa 404, permisos). Reutiliza `test_api_boards.py` para AC-03/AC-05 (409 sin destino); se agrega un caso de archivo de columna vacía tras mover/cerrar. `makemigrations --check`.
Frontend (Karma): servicios (cuerpos con `description`, importe omitido), página lista de tableros (AC-01, AC-02), página tablero (AC-03…AC-06: orden, menú, bloqueo 409, alta de tarjeta, recarga), diálogos, `sidebar-menu.spec.ts` (+1 título), paridad `i18n:check`.

## E2E
**NO** — el repo no tiene Playwright (dependencia nueva); la recarga se cubre con relectura en API y componente.

## Regression tests
Suites `crm` completas, Kanban de Oportunidades (diálogo con importe), `npm run i18n:check`, lint.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01, AC-02 | Karma lista de tableros + API boards existente |
| AC-03, AC-04 | Karma tablero + API stages |
| AC-05 | Karma tablero (409) + API archive |
| AC-06 | API opportunities + Karma diálogo/tablero |
| AC-07 | API opportunities + Karma Oportunidades |
| AC-08 | API opportunities/boards |

# Implementation Plan

## Architecture considerations
Sin ADR: una columna nueva y contrato aditivo dentro de `crm`.

## Proposed solution
Backend: `Opportunity.description` + importe opcional. Frontend: dos páginas (`crm-tracking-board-list`, `crm-tracking-board`), diálogo de columna (reutilizando `board-name-dialog`), diálogo de tarjeta propio y entrada de menú.

## Files/components affected
- Backend: `crm/domain/opportunity.py`, `infrastructure/django/models.py`, `migrations/0004_opportunity_description.py`, `application/opportunity_services.py`, `api/opportunity_serializers.py`, `api/opportunity_views.py` (si aplica), tests `test_domain_opportunity.py`, `test_api_opportunities.py`, `test_api_boards.py`.
- Frontend: `features/crm/` (`pages/crm-tracking-board-list`, `pages/crm-tracking-board`, `components/tracking-card-dialog`, `models/opportunity.ts`, `services/crm-opportunities-api.service.ts`, `crm.routes.ts`), `app.routes.ts`, `assets/data/routes.json`, `assets/i18n/{es,en,pt}.json`, `sidebar-menu.spec.ts`, `docs/design/design-system.md` §5.
- Migraciones: nueva `0004` (campo `description` con default vacío).

## Implementation steps
1. Dominio y modelo: descripción + importe opcional; migración 0004 (INV-03, INV-04).
2. Servicio, serializers y respuesta (API-01, AC-06/07).
3. Pruebas de dominio y API; `ruff`/`flake8` en lo cambiado (AC-06…08).
4. Frontend: modelos y servicio con `description`/importe opcional; ajustar diálogo de Oportunidades sin romperlo.
5. Página lista de tableros + modal (AC-01, AC-02).
6. Página tablero: columnas, menú, diálogos, bloqueo de archivo (AC-03…AC-06).
7. Rutas, menú, i18n es/en/pt, spec del menú, `design-system.md`.
8. `npm run i18n:check`, `npm run lint`, `npm test`.

## Database / migrations
Agrega `crm_opportunity.description` (varchar 1000, default ''); sin tocar datos.

## Risks
Importe opcional en `Opportunity.create` podría ocultar errores de captura en Oportunidades: el diálogo de Oportunidades sigue exigiéndolo en UI.

## New dependencies
Ninguna.
