# TASK-crm-listado-clientes: PB-CRM-001 · Listado de clientes CRM

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** `task/TASK-crm-listado-clientes` (base: `crm`)
**Pull Request:** _se completa al abrir el PR_
**Fuente:** https://trello.com/c/7VV7PNhI/4-pb-crm-001-listado-de-clientes-crm

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-24 | (nuevo) → INVESTIGATION | Task creado desde tarjeta de Trello | delivery-start |
| 2026-11-24 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | Decisiones de negocio respondidas por el usuario; DDR y ADR escritos | delivery-start |
| 2026-11-24 | PLANNING → ENGINEERING | Plan v1 COMPLETO, Specification READY; PR abierto contra `crm` | delivery-start |

## Investigación

### Requerimiento
Insumo (tarjeta Trello PB-CRM-001, no Specification aprobada): *Como vendedor, quiero encontrar clientes existentes para priorizar contactos.* Reutilizar clientes, pedidos y saldos; navegación CRM y filtros paginados. UI: menú CRM → Clientes; buscador, filtro de sucursal; columnas nombre, teléfono, última compra, pedidos y saldo; el filtro por segmento queda para PB-CRM-007. Backend: reusar Customer; exponer `customer_id, display_name, phone, last_purchase_at, order_count, outstanding_amount, currency` según datos existentes y agregados; sin campo `segment` en Customer ni membresías persistidas. Tests: API (búsqueda, filtro de sucursal, paginación, aislamiento) y Playwright (abrir ficha, estado vacío, listado sin segmentos). Habilita PB-CRM-002 y PB-CRM-008.

Aclaración del usuario: «usa la rama crm» (base y destino del PR). Respuestas: sucursal = almacén; sin filtro de segmento; saldo de pedidos no cancelados; Karma en lugar de Playwright.

### Hechos encontrados
- `origin/crm` apunta al mismo commit que `main` (`913b5286`); sin PR previo.
- `backend/modules/customers/api/views.py:57-64` — lista paginada con `search`/`active`; `customers/services.py` expone fachadas DTO.
- `backend/modules/sales/infrastructure/django/models.py:8-33` — `OrderModel` con `customer_id`, `warehouse_id` (nulo en históricos), `total`, `paid_total`, `order_date`.
- `backend/modules/sales/services.py:1-10` y `read_queries.py:17-22` — definiciones de pedido válido y saldo pendiente.
- `backend/modules/inventory/services.py:171` — `list_active_warehouses`; `config/urls.py` monta `api/warehouses/`.
- No existe concepto de sucursal ni de segmento en backend/docs (grep). Moneda: constante `BOB` (`sales/infrastructure/adapters.py:47`).
- Menú: `assets/data/routes.json:52-62`, rutas `app.routes.ts:210-216`; lista de referencia `features/customers/pages/customer-list`.
- No hay Playwright (solo Karma) en `frontend/panel_admin`.
- `docs/architecture/ddd.md:819-821` — dependencias permitidas solo por fachada; `sales → customers` existe, lo inverso no.

### Hipótesis / supuestos no confirmados
- «Última compra» = fecha del último pedido válido (no necesariamente entregado). Registrado en el PLAN.

### Módulos y dependencias relacionadas
`customers`, `sales`, `inventory`, `modularity` (lectura).

### Implementaciones similares existentes
`reporting` (módulo de solo lectura con puertos/adaptadores); `customer-list` y `movement-list` en frontend.

### Comportamiento actual
No hay forma de ver pedidos o saldo junto a cada cliente ni menú CRM.

### Restricciones
Aislamiento por `company_id`, `Decimal`, sin texto hardcodeado, sin dependencias nuevas, sin migraciones editadas.

### Riesgos identificados
Rendimiento del filtro por almacén con muchos clientes; pedidos históricos sin almacén.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — contexto nuevo que cruza tres módulos y fija dependencias permitidas.

### Diseño requerido
**SI** — pantalla nueva y menú nuevo.

## Diseño
`docs/design/DDR-crm-listado-clientes-menu-y-lista-crm.md`

## Arquitectura
`docs/adr/ADR-crm-listado-clientes-contexto-crm-de-solo-lectura.md`

## Plan
`docs/plans/PLAN-2026-11-24-crm-listado-clientes.md` (v1, COMPLETO, READY)

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
