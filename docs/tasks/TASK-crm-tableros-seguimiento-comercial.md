# TASK-crm-tableros-seguimiento-comercial: Seguimiento comercial: tableros, columnas y tarjetas

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** SI
**Rama:** `task/TASK-crm-tableros-seguimiento-comercial` (base `origin/crm`)
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/140 (base `crm`)
**Fuente:** https://trello.com/c/gEOASQIy/23-crm-crear-tableros-de-seguimiento-columnas-y-tarjetas

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-27 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-11-27 | INVESTIGATION → DESIGN → PLANNING | Veredicto NEEDS_PLAN, diseño SI; decisiones del usuario registradas | delivery-start |
| 2026-11-27 | PLANNING → ENGINEERING | Specification READY | delivery-start |
| 2026-11-27 | ENGINEERING → REVIEW | Implementación completa | delivery-build |

## Investigación

### Requerimiento
Tarjeta Trello «CRM · Crear tableros de seguimiento, columnas y tarjetas» (insumo, no Specification aprobada). Historia: como usuario del CRM quiero crear tableros, organizar columnas y registrar tarjetas vinculadas a clientes o prospectos. Criterios resumidos:
- CRM → Seguimiento comercial: cada tablero es una tarjeta con su nombre; al elegirla abre el tablero. «Crear nuevo tablero» abre un modal solo con nombre (obligatorio); el tablero nuevo nace **sin columnas** y con «Agregar columna» disponible.
- Columnas: «Agregar columna» pide nombre obligatorio; la primera a la izquierda, las siguientes a la derecha de la última. Encabezado con nombre y botón de tres puntos (menú «Agregar tarjeta» y «Archivar columna»). Columna vacía se archiva; con tarjetas activas se **bloquea** con aviso de moverlas primero.
- Tarjetas: formulario con **Nombre** y **Cliente o prospecto** obligatorios y **Descripción** opcional; selector de clientes y prospectos de la misma empresa; la tarjeta aparece por su nombre en la columna de origen. Tableros, orden de columnas y tarjetas persisten al recargar.
- Alcance: reutiliza PB-CRM-001 (clientes), PB-CRM-003 (tableros/columnas) y PB-CRM-004 (vínculos a cliente/prospecto). «Iniciar sin columnas» solo aplica a tableros nuevos; los existentes conservan columnas y tarjetas. Tareas e historial dentro de la tarjeta son PB-CRM-005.

Aclaración del usuario: «usa la rama de CRM» (base `origin/crm`; se fusionó `origin/crm` en la rama de trabajo).
Decisiones del usuario (AskUserQuestion, 2026-11-27): (1) la tarjeta de seguimiento **es la oportunidad** (se le agrega descripción; el importe pasa a opcional); (2) archivar columna con tarjetas **bloquea solo en la nueva pantalla**, el editor «Tablero» conserva su reasignación; (3) **entrada de menú nueva** «Seguimiento comercial», Oportunidades y Tablero se mantienen.

### Hechos encontrados
- Tableros y etapas ya existen: `backend/modules/crm/domain/board.py` (`Board`, `add_stage`, `reorder`, `validate_stage_archive:99`), `application/services.py` (`BoardService`, `archive_stage:65`), API `/api/crm/boards/` (`api/board_urls.py`).
- Archivar etapa con tarjetas sin destino ya responde 409 `stage_has_cards` con `card_count` (`domain/board.py:102-104`); con `target_stage_id` reasigna (`services.py:69-71`).
- Los tableros nuevos y el «Ventas» automático nacen sin etapas (PLAN PB-CRM-003; `infrastructure/defaults.py`). Agregar etapa la pone al final (INV-02).
- Las tarjetas son oportunidades: `OpportunityModel` (`infrastructure/django/models.py:62-82`) con `board`, `stage`, `lead` (FK) o `customer_id`, `title` (≤150), `amount` obligatorio `Decimal(12,2)`, `owner_id`; sin campo de descripción. `Opportunity.create` exige prospecto o cliente (`domain/opportunity.py`), título obligatorio, importe obligatorio.
- `OpportunityService.create` (`application/opportunity_services.py:115`) valida tablero activo, prospecto/cliente de la empresa, etapa inicial (primera activa por defecto; 409 `board_has_no_stages` si no hay).
- API de oportunidades en `/api/crm/opportunities/` (`api/opportunity_urls.py`); serializer de alta con `amount` obligatorio (`api/opportunity_serializers.py:14-23`).
- Tareas y actividades cuelgan de oportunidades (`models.py:118-130`), por eso la tarjeta debe seguir siendo oportunidad.
- Frontend: `features/crm/pages/crm-board` (editor admin), `pages/crm-opportunity-board` (Kanban con arrastre, filtros, diálogos), `components/opportunity-dialog` (título, contacto con `ng-select`, importe, siguiente acción, responsable), `components/board-name-dialog`, servicios `crm-boards-api.service.ts` y `crm-opportunities-api.service.ts`, rutas en `crm.routes.ts`, menú en `assets/data/routes.json` (CRM, claves `MENUITEMS.CRM.*`) y conteo de menú en `layout/sidebar/sidebar-menu.spec.ts`.
- La etiqueta i18n `CRM.BOARD.SEGUIMIENTO_COMERCIAL` ya existe (`assets/i18n/es.json:3698`) y la usa el editor `crm-board.component.html`; la nueva entrada de menú usa claves propias.

### Hipótesis / supuestos no confirmados
- Una tarjeta nueva sin importe se guarda con importe 0 BOB y responsable = usuario autenticado (derivado de «la tarjeta solo pide nombre, contacto y descripción»; el modelo exige ambos).
- «Tarjetas activas» = oportunidades abiertas (lo que cuenta `card_count`); las cerradas no bloquean el archivo.
- El nombre de la tarjeta se guarda en `title`.

### Módulos y dependencias relacionadas
`crm` (único contexto escrito), lectura de `customers` por fachada existente; `modularity` (módulo `customers`).

### Implementaciones similares existentes
Kanban de oportunidades (`crm-opportunity-board`), editor de etapas (`crm-board`), `board-name-dialog`, `opportunity-dialog`.

### Comportamiento actual
Hoy existen el editor admin «Tablero» (columnas con Subir/Bajar y archivo con reasignación) y el Kanban «Oportunidades» (tarjetas con importe obligatorio); no hay lista de tableros como tarjetas ni alta de columnas/tarjetas desde el propio tablero.

### Restricciones
Aislamiento por `company_id`; dinero en `Decimal`; no editar migraciones aplicadas (se agrega `0004`); sin texto hardcodeado (i18n es/en/pt); sin dependencias nuevas.

### Riesgos identificados
Cambiar el importe a opcional no debe romper la lista/Kanban de Oportunidades ni los cierres; la migración añade columna con valor por defecto vacío (sin datos tocados).

### Veredicto de complejidad
**NEEDS_PLAN** — cambio acotado dentro del contexto `crm`: una columna nueva, un ajuste de contrato y dos pantallas nuevas reutilizando servicios y diálogos; sin decisión arquitectónica nueva.

### Diseño requerido
**SI** — pantallas nuevas (lista de tableros y tablero con columnas/menús/diálogos).

## Diseño
`docs/design/DDR-crm-tableros-seguimiento-comercial-lista-de-tableros-y-tablero.md`.

## Arquitectura
No aplica según veredicto.

## Plan
`docs/plans/PLAN-2026-11-27-crm-tableros-seguimiento-comercial.md` (v1, COMPLETO, READY).

## Implementación
**Backend** (`backend/modules/crm/`): `Opportunity.description` (INV-03) e importe opcional con 0.00 por defecto (INV-04) en dominio, modelo, repositorio, servicio y serializers; migración `0004_opportunity_description`; la API devuelve y acepta `description` (API-01). Archivar columna reutiliza el 409 `stage_has_cards` existente (INV-05), sin cambios de API.
**Frontend** (`features/crm/`): páginas `crm-tracking-board-list` (AC-01, AC-02) y `crm-tracking-board` (AC-03…AC-06), diálogos `stage-name-dialog` y `tracking-card-dialog`, modelo/servicio con `description` e importe opcional (API-01), ruta `/pocketbiz/crm/tracking[/:boardId]`, entrada de menú, claves i18n `CRM.TRACKING.*` y `MENUITEMS.CRM.LIST.TRACKING` en es/en/pt.
**UI de referencia:** `crm-opportunity-board` (Kanban) y `crm-board`; reutiliza `board-name-dialog` (crear tablero), `ng-select` y `ngbDropdown`. `design-system.md` §5 ampliado con la variante.
**Desviaciones / notas:**
- La rama `origin/crm` se fusionó con `main` (merge `4b3fec76`): el conflicto del conteo del menú se resolvió; el merge dejó el bloque CRM de `routes.json` con `id: "dentistry"` y sin id el de Odontología, ya corregido (`id: "crm"`). Con `id: "crm"` el CRM queda en la cola previa a Ajustes en los menús por tipo de empresa (`menu-layout.ts` no lo nombra): `menu-layout.spec.ts` lo refleja; ubicarlo en el orden de cada tipo es decisión de producto pendiente.
- «Tarjetas activas» = oportunidades abiertas (`card_count`), como en PB-CRM-004.
**Pruebas:** dominio (`test_domain_opportunity.py`, 17 OK ejecutadas); API (`TrackingCardTests` y validación de `description` en `test_api_opportunities.py`) **escritas pero no ejecutadas** localmente: el worktree no tiene `.env` ni credenciales de PostgreSQL (regla del proyecto: no tocar `.env`); `ruff`/`flake8` limpios en lo cambiado; `makemigrations --check` sin cambios. Frontend: Karma 2090/2090, `ng lint` y `i18n:check` limpios, `ng build` compila.
**Deuda técnica:** la tarjeta no abre detalle ni se edita desde la nueva pantalla (PB-CRM-005).

## Review
_Pendiente_

## Publicación
_Pendiente_
