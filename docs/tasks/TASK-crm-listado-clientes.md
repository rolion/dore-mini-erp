# TASK-crm-listado-clientes: PB-CRM-001 · Listado de clientes CRM

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** `task/TASK-crm-listado-clientes` (base: `crm`)
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/120
**Fuente:** https://trello.com/c/7VV7PNhI/4-pb-crm-001-listado-de-clientes-crm

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-24 | (nuevo) → INVESTIGATION | Task creado desde tarjeta de Trello | delivery-start |
| 2026-11-24 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | Decisiones de negocio respondidas por el usuario; DDR y ADR escritos | delivery-start |
| 2026-11-24 | PLANNING → ENGINEERING | Plan v1 COMPLETO, Specification READY; PR abierto contra `crm` | delivery-start |
| 2026-11-24 | ENGINEERING → REVIEW | Implementación completa según plan v1 | delivery-build |
| 2026-11-24 | REVIEW → PUBLISH | Quality Gate PASS (sin Critical/High); 2 Medium y 2 Low abiertos (REV-01…04) | delivery-publish |
| 2026-11-24 | PUBLISH (sin cambio) | REV-01…04 corregidos (e0b9dc49) y Quality Gate repetido: PASS (backend 2412, frontend 1828) | delivery-publish |
| 2026-11-24 | PUBLISH (sin cambio) | PR listo para aprobación humana; cambio con ADR (contexto nuevo), no se mergea | delivery-publish |

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
**Resumen:** contexto `crm` de solo lectura (`backend/modules/crm/`: puertos, caso de uso `ListCrmCustomers`, adaptadores, vista `GET /api/crm/customers/`), fachadas `customers.search_customers_for_crm`, `sales.get_customer_commercial_summaries` y `sales.list_customer_ids_with_orders_in_warehouse`; frontend `features/crm` (lista, servicio, modelos, fixtures), submenú CRM en `routes.json`, ruta `crm/customers` e i18n es/en/pt.

**Cobertura:** AC-01…AC-05, AC-08 y AC-09 en `crm/tests/test_api.py`; AC-06 en `sidebar-menu.spec.ts` y el spec de la lista; AC-07 y AC-08 en el spec de la lista; INV-01…INV-04 en las pruebas de API. Pruebas propias (no es el Quality Gate): backend 2403 OK en PostgreSQL (venv del checkout principal, Django 5.2.17), `flake8`/`ruff` limpios en lo cambiado, `makemigrations --check` sin cambios; frontend `ng build`, `ng lint`, `i18n:check` y 1827 specs OK.

**Desviaciones respecto al plan:** (1) la disponibilidad de Ventas/Inventario se lee con `shared.module_gate` en lugar de `modularity.services` (ADR actualizado); (2) menú: el submenú CRM se inserta tras «Cliente» y se actualizó `sidebar-menu.spec.ts` (16 rutas, 50 títulos); (3) no se añadió índice a `sales_order.warehouse_id` (no se midió necesidad; sin migraciones).

**Deuda técnica:** filtro de sucursal con lista de ids (aceptable al volumen del MVP); `last_purchase_at` es una fecha, no un instante; moneda fija `BOB`.

**UI:** referencia «Lista de solo lectura con filtros» (`inventory/pages/movement-list`, `customers/pages/customer-list`); reutiliza el pipe `money`, `ngx-datatable`, `NgbCollapse`/`NgbPagination` y `WarehousesApiService` vía `features/inventory/index.ts`; no se crearon componentes compartidos.

## Review
**Veredicto: PASS** (Quality Gate en subagente aislado, sobre el estado `HEAD` de la rama).

Ejecutado: backend suite completa 2403 OK (PostgreSQL, Django 5.2); frontend 1827 specs OK (cobertura `features/crm`: página 95 % líneas, servicios 100 %); `ruff` y `flake8` limpios; `bandit -r modules/crm` sin hallazgos; `makemigrations --check` sin cambios; `npm run lint`, `i18n:check`, `ng build` OK; `npm audit` 0 vulnerabilidades. No ejecutado: revisión visual en navegador (claro/oscuro, 390/1440 px; solo revisión estática) y E2E (el plan fija E2E: NO).

Hallazgos: REV-01 a REV-04 **cerrados** (corregidos en `e0b9dc49`). Segunda pasada del Quality Gate sobre el estado final: **PASS** — backend suite completa 2412 OK, frontend 1828 OK, `ruff`/`flake8` limpios, `makemigrations --check` sin cambios, `lint`, `i18n:check` y `ng build` OK. Sin hallazgos nuevos. Observaciones menores sin REV: la tarjeta móvil de la fecha se verificó solo por lectura del diff, y la guarda defensiva de saldo (`total > paid_total`) no es alcanzable por el dominio (impide el sobrepago) y queda sin prueba. Revisión visual en navegador (2026-11-24, API y app locales con datos de prueba temporales, ya borrados): lista de escritorio, filtro de sucursal (URL actualizada, agregados globales), búsqueda, vacío filtrado con badges, tarjetas y panel «Filtros» a 375 px, menú CRM → Clientes y apertura de la ficha desde un resultado, todo conforme. Modo oscuro: no verificable (el tema de la plantilla no sigue `prefers-color-scheme`).

## Publicación
PR #120 completo y listo para aprobación humana (base `crm`). Cambio sensible: introduce un contexto nuevo con dependencias entre módulos (ADR-crm-listado-clientes-contexto-crm-de-solo-lectura); no toca autenticación, migraciones ni infraestructura. No se mergea desde el flujo.
