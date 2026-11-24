# TASK-crm-prospectos-oportunidades: PB-CRM-004 · Prospectos y oportunidades

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** `task/TASK-crm-prospectos-oportunidades` (base: `crm`)
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/122
**Fuente:** https://trello.com/c/kQtkFFfv/5-pb-crm-004-prospectos-y-oportunidades

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-24 | (nuevo) → INVESTIGATION | Task creado desde tarjeta de Trello | delivery-start |
| 2026-11-24 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | Decisiones de negocio respondidas por el usuario; DDR y ADR escritos | delivery-start |
| 2026-11-24 | PLANNING → ENGINEERING | Plan v1 COMPLETO, Specification READY; PR abierto contra `crm` | delivery-start |
| 2026-11-24 | ENGINEERING → REVIEW | Implementación completa según PLAN v1 | delivery-build |
| 2026-11-24 | REVIEW → PUBLISH | Quality Gate PASS (REV-01 Medium, REV-02 y REV-03 Low abiertos) | delivery-publish |
| 2026-11-24 | PUBLISH | REV-01 corregido (colores del Kanban y prospectos en tema oscuro) | delivery-build |

## Investigación

### Requerimiento
Insumo (tarjeta Trello PB-CRM-004, no Specification aprobada): *Como vendedor, quiero mover posibles ventas y convertir prospectos en clientes sin duplicados.* Gestionar oportunidades por operación con resultado ganado o perdido y vínculo opcional a pedido. UI: Kanban con filtros por responsable y prospecto; tarjeta con contacto, importe y siguiente acción; formulario de cierre, conversión y selector de pedidos. Backend: `Lead` (company_id, name, normalized_phone, email, converted_customer_id) y `Opportunity` (board_id, stage_id, lead_id o customer_id, title, owner_id, amount, currency, next_action_at, status, closed_at, order_id, lost_reason); registrar cambios de etapa. Tests: API (mover solo dentro del tablero, cerrar y convertir de forma idempotente, impedir vínculos entre empresas) y Playwright (consulta → venta ganada → pedido). Depende de PB-CRM-003; habilita PB-CRM-005, -006 y -012.

Aclaraciones del usuario: «usa la rama crm» (base y destino del PR; ya contiene PB-CRM-003, PR 121). Respuestas de negocio (2026-11-24):
1. Conversión con teléfono ya existente → **vincular al cliente existente** (sin crear duplicado; con varios coincidentes se elige uno).
2. Cierre: **perdida exige motivo; ganada sin requisitos**; una oportunidad cerrada no se reabre ni se mueve.
3. Pedido vinculable: de la misma empresa, **del mismo cliente** de la oportunidad (exige cliente), **no cancelado**, y **uno a uno** (un pedido solo en una oportunidad).
4. Responsable = usuario de la misma empresa (por defecto quien crea); moneda `BOB` fija.
Por coherencia con PB-CRM-003 (decisión del usuario allí) se usa Karma en lugar de Playwright.

### Hechos encontrados
- `origin/crm` ya contiene PB-CRM-003 (`dd8981ef`): `backend/modules/crm/` con `domain/board.py`, `application/{ports,services}.py`, modelos `BoardModel`/`StageModel` (`infrastructure/django/models.py:7-39`) y API `/api/crm/boards/` (`api/board_urls.py`).
- `backend/modules/crm/application/ports.py:45-50` — puerto `StageCards` (`count`, `reassign`) con adaptador nulo `NoCards` (`infrastructure/adapters.py:77-84`), conectado en `api/board_views.py:15-18` (`stage_cards(company_id)`): PB-CRM-004 debe sustituirlo. `BoardService.archive_stage` ya reasigna en transacción (`application/services.py:65-73`) y `card_count` suma por etapa (`:14-15`).
- `backend/modules/crm/infrastructure/adapters.py:1-75` — único lugar de CRM que importa fachadas `services.py` de `customers`, `sales`, `inventory` y `shared.module_gate`.
- `backend/modules/customers/domain/customer.py:23-66` — `normalize_phone(raw, default_country_code)`; `customers/application/commands.py:18-27` — `CreateCustomer` detecta teléfono duplicado (`DuplicateCustomerPhone`); `customers/infrastructure/django/repositories.py:67-71` — `find_by_phone`. `customers/services.py:73-130` — fachadas existentes para CRM e importación.
- `backend/modules/sales/infrastructure/django/models.py:7-37` — `OrderModel` (`company_id`, `customer_id`, `status`, `total`); `sales/services.py` no expone aún consulta de pedidos por cliente para CRM (se añade fachada).
- `backend/shared/identity.py:6-30` — `CompanyUserDirectory(company_id)` (`exists(user_id)`, `list`): único modo de validar responsables sin importar `accounts`; el id de usuario es entero (`accounting/.../models.py:214` usa `BigIntegerField`).
- `backend/shared/tenancy.py` — `company_id_from(request)`; `config/permissions.py:22-30` exige `required_modules` en cada vista (`('customers',)` en CRM).
- `frontend/panel_admin/src/app/features/crm/` — `crm-board` (editor de etapas), `crm-customer-list`, `crm-boards-api.service.ts` (patrón de servicio + `CrmApiError`), `testing/crm-fixtures.ts`; `docs/design/design-system.md:148` plantilla «Editor de lista ordenable»; menú CRM en `assets/data/routes.json:74-85`; no hay Playwright.
- `docs/architecture/ddd.md:848,1532` — notas de CRM: dependencias solo por fachada y desde `infrastructure/adapters.py`.

### Hipótesis / supuestos no confirmados
- La «siguiente acción» de la tarjeta se representa solo con `next_action_at` (fecha/hora), tal como pide la tarjeta; sin texto de acción (lo traerá PB-CRM-005, Tareas).
- Orden de tarjetas dentro de una columna: por fecha de creación; sin ordenamiento manual (fuera de alcance).
- Mover tarjetas con control accesible («Mover a…» + botones), no arrastrar y soltar, igual que PB-CRM-003.
- Con varios clientes coincidentes por teléfono, la persona elige uno en el diálogo; el backend responde 409 `multiple_customer_matches` con candidatos.
- Contar y reasignar al archivar etapa/tablero solo considera oportunidades **abiertas**; las cerradas conservan su etapa como dato histórico.

### Módulos y dependencias relacionadas
`crm` (primeras entidades de negocio), `customers` (normalizar teléfono, buscar por teléfono, crear cliente: nuevas fachadas), `sales` (consultar/listar pedidos del cliente: nueva fachada), `shared.identity` (responsables), `shared.module_gate` (Ventas opcional).

### Implementaciones similares existentes
`crm` boards (dominio puro + `BoardService` + repositorio por empresa + vistas finas), `customers/application/commands.py` (alta con aviso de duplicado), `service_catalog`/`quotations` (listas paginadas con filtros), `features/purchases/pages/purchase-list` (lista con estados).

### Comportamiento actual
No existen prospectos ni oportunidades; el tablero no tiene tarjetas (`card_count` siempre 0, `NoCards`). El listado de clientes de CRM es de solo lectura.

### Restricciones
Aislamiento por `company_id` (ids ajenos → 404, vínculos entre empresas imposibles); `crm` no importa `accounts` ni infraestructura de otros módulos; `Decimal` para importes; migración nueva (nunca editar la `0001`); sin dependencias nuevas; textos i18n es/en/pt; escrituras atómicas e idempotentes.

### Riesgos identificados
- Conversión concurrente del mismo prospecto (doble clic / dos usuarios): bloqueo de fila del prospecto + idempotencia.
- Pedido vinculado a dos oportunidades en carrera: restricción única condicional en BD.
- Acoplamiento nuevo de `crm` hacia `customers.services` y `sales.services`: solo por fachada y desde `adapters.py`.
- Kanban con muchas tarjetas: carga limitada (pagina de hasta 200 abiertas por tablero); aceptable para el MVP.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — nuevas entidades y migración, contrato API amplio, dependencias nuevas hacia `customers` y `sales`, adaptador real del puerto `StageCards` con transaccionalidad y reglas de idempotencia entre contextos.

### Diseño requerido
**SI** — pantallas nuevas (Prospectos, Kanban de oportunidades) y flujos de varios pasos (cierre, conversión, vínculo a pedido).

## Diseño
Ver `docs/design/DDR-crm-prospectos-oportunidades-kanban-y-prospectos.md` (propuesto).

## Arquitectura
Ver `docs/adr/ADR-crm-prospectos-oportunidades-modelo-conversion-y-vinculos.md` (propuesto).

## Plan
`docs/plans/PLAN-2026-11-24-crm-prospectos-oportunidades.md` (v1, COMPLETO, Specification READY).

## Implementación
Implementado según PLAN v1 (backend en `backend/modules/crm/`, fachadas en `customers`/`sales`, frontend en `features/crm/`).

- **Backend:** dominio `Lead`/`Opportunity` (INV-01…04, 07), modelos y migración `crm 0002` (INV-03, INV-08), `DjangoStageCards` en lugar de `NoCards` (INV-09, AC-08), conversión y cierre idempotentes (AC-04, AC-05), vínculo a pedido con códigos 409 (AC-06), API `/api/crm/leads/` y `/api/crm/opportunities/` (AC-01…03, 07, 09). Pruebas: `test_domain_opportunity`, `test_api_leads`, `test_api_opportunities`, fachadas de `customers`/`sales`, `test_boundaries`.
- **Frontend:** páginas `crm-opportunity-board` (Kanban) y `crm-lead-list`, diálogos de prospecto, oportunidad, cierre y conversión, servicios API, rutas y menú, 100 claves i18n es/en/pt (AC-10, AC-11). Referencias: plantilla Kanban nueva del DDR, `product-list` (lista) y el patrón de diálogo con motivo; se reutilizan `money`, `ModulesService` y `CrmApiError` ampliado.
- **Desviaciones (detalle de implementación):** fachada extra `customers.get_customers_for_crm` (sin N+1); códigos extra `opportunity_closed`, `opportunity_not_won` y `already_converted`; una oportunidad nueva de un prospecto ya convertido hereda su cliente; mover a la misma etapa no escribe historial; `GET /opportunities/<id>/orders/` excluye pedidos ya vinculados. El plan no define endpoint de usuarios de la empresa: el selector/filtro de responsable ofrece el usuario actual y los responsables ya vistos en el tablero, y el filtro de prospecto/cliente se arma con los contactos ya cargados (deuda: endpoint de usuarios y búsqueda libre). Cartas de oportunidades cerradas en etapas archivadas se agrupan en «Etapas archivadas».
- **Deuda técnica:** sin arrastrar y soltar; sin detalle de oportunidad (PB-CRM-005); límite de 200 tarjetas por carga.
- **Verificación propia (no es el Quality Gate):** backend `modules.crm modules.customers modules.sales` (604 pruebas) y `shared` pasan con PostgreSQL; `makemigrations --check` sin cambios; frontend `i18n:check`, `lint`, `build` y `npm test` (1895) pasan. No se probó contra un navegador real ni el flujo Kanban de punta a punta con el backend.

## Review
Quality Gate (subagente aislado, 2026-11-24): **PASS con observaciones**. Backend 616 pruebas OK, `makemigrations --check` sin cambios, ruff/flake8 sin avisos nuevos, bandit sin hallazgos; frontend `i18n:check`, `lint`, `build` OK, 1895 pruebas OK (cobertura global líneas 89,63 %), `npm audit` 0 vulnerabilidades. Revisión visual verificada en 390 y 1440 px, tema claro y oscuro. Sin E2E (decisión del plan) ni mypy (no configurado).
- REV-01 (Medium, IMPLEMENTATION, RESUELTO): Kanban ilegible en tema oscuro — `docs/reviews/REV-2026-11-24-crm-prospectos-oportunidades-01.md`.
- REV-02 (Low, IMPLEMENTATION, abierto): faltan pruebas de concurrencia simulada y del camino `IntegrityError` → `order_already_linked` — `...-02.md`.
- REV-03 (Low, PLAN, abierto): sin endpoint de usuarios de la empresa ni búsqueda libre de prospecto/cliente — `...-03.md`.

## Publicación
PR 122 listo para aprobación humana (no se mergea). Tarea con arquitectura (ADR), base de datos (migración `crm 0002`): requiere aprobación humana explícita. REV-01 corregido (tema oscuro).
