# PLAN-2026-11-24-crm-listado-clientes (v1)

**Task:** TASK-crm-listado-clientes · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** `docs/design/DDR-crm-listado-clientes-menu-y-lista-crm.md` · `docs/adr/ADR-crm-listado-clientes-contexto-crm-de-solo-lectura.md`

## Objective
Entregar «CRM → Clientes»: listado paginado de clientes activos con búsqueda, filtro de sucursal (almacén) y columnas nombre, teléfono, última compra, pedidos y saldo, reutilizando Clientes, Ventas e Inventario.

## Context
Historia PB-CRM-001 (Trello, ver TASK). Decisiones del usuario: sucursal = almacén; sin filtro de segmento (PB-CRM-007); saldo de pedidos no cancelados; pruebas de UI con Karma en lugar de Playwright. Rama de integración: `crm`.

# Specification

## Domain context
Bounded context nuevo `crm` (lectura) sobre `customers`, `sales`, `inventory` (ADR).

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Sucursal | Almacén activo de Inventario; un cliente pertenece a ella si tiene ≥1 pedido válido con ese `warehouse_id` | decisión del usuario |
| Pedido válido | No cancelado y con ítems | `sales/services.py:1-10` |
| Saldo (`outstanding_amount`) | Σ(`total − paid_total`) de pedidos válidos con saldo > 0 | `sales/services.py:10` |
| Última compra | Mayor `order_date` de pedidos válidos | nuevo, derivado |

## Current behavior
- `GET /api/customers/` filtra por `search`/`active` y pagina (`customers/api/views.py:57-64`); sin datos de ventas.
- No existen sucursales ni segmentos; el pedido guarda `warehouse_id` nulo en históricos (`sales/infrastructure/django/models.py:15-16`).
- No hay menú CRM; «Cliente» es ítem directo (`assets/data/routes.json:52-62`).

## Expected behavior
Ver ADR y DDR. La persona abre CRM → Clientes, busca por nombre o teléfono, filtra por sucursal y navega páginas; cada fila muestra los agregados y enlaza a la ficha.

## Domain rules / invariants
- INV-01 (existente): todo dato filtra por `company_id` del token; un id de otra empresa no se revela.
- INV-02 (nueva): los agregados salen solo de pedidos válidos y no dependen del filtro de sucursal (siempre son totales del cliente).
- INV-03 (nueva): el listado incluye solo clientes activos.
- INV-04: no se persiste ningún segmento ni membresía; no se agrega `segment` a Customer.

## Acceptance criteria
- AC-01 Búsqueda: `search` coincide parcialmente con nombre o teléfono (misma regla que Clientes).
- AC-02 Sucursal: `warehouse_id` devuelve solo clientes con ≥1 pedido válido en ese almacén; un almacén inexistente o de otra empresa → 400.
- AC-03 Paginación: `page`/`page_size` (máx. 100), `count` correcto, orden estable por nombre e id.
- AC-04 Aislamiento: nunca aparecen clientes, pedidos ni almacenes de otra empresa.
- AC-05 Campos por fila: `customer_id`, `display_name`, `phone`, `last_purchase_at`, `order_count`, `outstanding_amount` (Decimal como cadena), `currency` (`BOB`). Cliente sin pedidos: `last_purchase_at = null`, `order_count = 0`, `outstanding_amount = "0.00"`.
- AC-06 Menú y ficha: submenú CRM → Clientes visible con `customers` habilitado; el nombre abre la ficha del cliente.
- AC-07 Estado vacío: sin resultados se muestra el estado vacío (con y sin filtros, según DDR).
- AC-08 Sin segmentos: el listado funciona completo sin ninguna configuración de segmentos.
- AC-09 Módulos opcionales: sin Ventas, la API no calcula agregados y `meta.sales_enabled=false`; sin Inventario, `meta.warehouse_filter_enabled=false` y `warehouse_id` se rechaza con 400. La UI oculta lo no disponible.

## Edge cases / Error cases
`page_size` inválido o `warehouse_id` no UUID → 400; página fuera de rango → 404 (DRF); cliente sin teléfono → `phone: ""`; pedidos sin `warehouse_id` no coinciden con ningún almacén; `search` vacío = sin filtro.

## Authorization / permissions
Usuario autenticado con empresa; `required_modules = ('customers',)`; mismas reglas que `/api/customers/`. Usuario sin empresa → 403.

## API contract
- API-01 `GET /api/crm/customers/?search=&warehouse_id=&page=&page_size=` → `{count, next, previous, results[...], meta: {sales_enabled, warehouse_filter_enabled}}`.
- API-02 Filas según AC-05. `last_purchase_at` es fecha ISO (`YYYY-MM-DD`).
- Compatibilidad: endpoint nuevo; no cambian contratos existentes. El selector de sucursales usa `GET /api/warehouses/` existente.

## UI behavior
- UI-01 Lista de solo lectura con filtros + variante compacta (design-system §5), DDR sección «Componentes».
- UI-02 Estados cargando/vacío/vacío filtrado/error según DDR; filtros y página en la URL.
- UI-03 Menú: submenú CRM con «Clientes»; textos por claves i18n es/en/pt.

## Non-functional requirements
Agregados de Ventas en una consulta por página (sin N+1); sin migraciones.

## Out of scope
Segmentos y su filtro (PB-CRM-007), ficha 360° (PB-CRM-002), acciones de recompra (PB-CRM-008), moneda por empresa, ordenamiento por columnas, exportación, clientes inactivos, Playwright.

## Open questions
Ninguna bloqueante.

# Test Specification

## Unit tests / Integration tests
- Backend (`crm/tests`): API para AC-01…AC-05, AC-09; fuga entre empresas (AC-04); fachadas `sales`/`customers` (agregados, pedidos cancelados/sin ítems excluidos, saldo); `test_boundaries.py` actualizado con `crm → …`.
- Frontend (Karma): servicio API, componente de lista (columnas, búsqueda, filtro, paginación, estado vacío, enlace a ficha, ocultar columnas sin Ventas), menú (`sidebar-menu.spec.ts`), paridad i18n.
## E2E
**NO** — el usuario decidió Karma en lugar de instalar Playwright (dependencia nueva); AC-06/07/08 se cubren con pruebas de componente y de menú.
## Regression tests
Suites de `customers`, `sales`, `reporting`, boundaries y sidebar existentes.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | API test búsqueda nombre/teléfono |
| AC-02 | API test filtro y 400 de almacén ajeno |
| AC-03 | API test paginación y orden |
| AC-04 | API test dos empresas |
| AC-05 | API test cliente con y sin pedidos; test de fachada de Ventas |
| AC-06 | `sidebar-menu.spec.ts`; spec de componente (enlace a ficha) |
| AC-07 | Spec de componente (vacío con/sin filtros) |
| AC-08 | API test sin segmentos + spec de componente |
| AC-09 | API test con módulos deshabilitados; spec de componente |

# Implementation Plan

## Architecture considerations
ADR: contexto `crm` de solo lectura, composición por fachadas, sin clave de módulo nueva.

## Proposed solution
Fachadas en `customers` y `sales`; casos de uso `ListCrmCustomers` en `crm/application` con puertos (`CustomerSearch`, `SalesSummaries`, `WarehouseDirectory`, `ModuleAvailability`); adaptadores en `crm/infrastructure/adapters.py`; vista DRF con paginador propio sobre resultado perezoso.

## Files/components affected
- Backend: `modules/crm/**` (nuevo, registrar en `INSTALLED_APPS` y `config/urls.py` → `api/crm/`), `customers/services.py`, `sales/services.py` y `sales/infrastructure/django/read_queries.py`, `sales/tests/test_boundaries.py`, `docs/architecture/ddd.md`.
- Frontend: `features/crm/**` (routes, page, service, models, testing), `app.routes.ts`, `assets/data/routes.json`, `assets/i18n/{es,en,pt}.json`, `sidebar-menu.spec.ts`.
- Docs: `docs/design/design-system.md` §6 (nota del submenú CRM).

## Implementation steps
1. Fachadas `customers.search_customers_for_crm` y `sales.get_customer_commercial_summaries` / `list_customer_ids_with_orders_in_warehouse` + tests (AC-01, AC-05, INV-02/03).
2. Módulo `crm`: puertos, caso de uso, adaptadores, vista, URL, paginación (AC-02, AC-03, AC-09).
3. Tests API y de fronteras (AC-01…AC-05, AC-08, AC-09, INV-01).
4. Frontend: modelos, servicio, página de lista y variante compacta (UI-01, UI-02).
5. Menú CRM, ruta, i18n es/en/pt (AC-06, UI-03).
6. Specs de componente/servicio/menú (AC-06, AC-07, AC-08).
7. Actualizar `ddd.md` y `design-system.md`; lint de lo cambiado.

## Database / migrations
Ninguna. Índices existentes: `sales_order.customer_id`, `customers_customer.company_id`/`phone` (verificar en build si `warehouse_id` necesita índice; si sí, migración nueva).

## Risks
Filtro por lista de ids en clientes grandes; pedidos históricos sin almacén; el nombre «last_purchase_at» es una fecha (documentado en API-02).

## New dependencies
Ninguna.
