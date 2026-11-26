# TASK-reporte-ingresos-por-venta: Reporte «Ingresos por venta» (ventas entregadas y pagadas)

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** SI
**Rama:** task/TASK-reporte-ingresos-por-venta
**Pull Request:** _se completa al abrir el PR_

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-26 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-11-26 | INVESTIGATION → DESIGN → PLANNING | Veredicto NEEDS_PLAN, diseño requerido; DDR y PLAN v1 | delivery-start |
| 2026-11-26 | PLANNING → ENGINEERING | Specification READY, PR abierto | delivery-start |

## Investigación

### Requerimiento
«En módulo de ventas debemos agregar un reporte de ventas finalizadas y pagadas. Será un submenú de Ventas, "Reporte ingresos por venta". Filtros: fecha inicio, fecha fin, período fiscal. Por defecto trae todas las ventas pagadas hasta la fecha, paginadas. Se debe poder exportar a PDF y Excel. Columnas: pedido, cliente, total, saldo.»

### Hechos encontrados
- `backend/modules/sales/domain/enums.py:4-24` — `OrderStatus` (`DELIVERED` = entregado/finalizado) y `PaymentStatus` (`PAID`).
- `backend/modules/sales/domain/repositories.py:19-60` — `OrderFilters` ya admite `statuses`, `payment_statuses`, `customer_id`, `date_from/date_to` (sobre `order_date`); `OrderSummary` expone `code`, `total`, `paid_total` y `balance`.
- `backend/modules/sales/infrastructure/django/repositories.py:76-98` — `list(filters)` aplica esos filtros por `company_id`; no filtra por período fiscal.
- `backend/modules/sales/infrastructure/django/models.py:30-32` — el pedido guarda `fiscal_period_id` (UUID sin FK) y `fiscal_period_name` (instantánea) al numerarse; `OrderSummary.number.period_id` lo refleja (`mappers.py:28,57,79`).
- `backend/modules/sales/api/views.py:172-183` y `api/pagination.py` — la lista usa `ListOrders`, `OrderPagination` (`page_size` máx. 100) y nombres de clientes vía `CustomerDirectoryAdapter` (con Clientes deshabilitado `customers_available` es falso).
- `backend/modules/sales/api/urls.py:21-37` — `<str:order_id>/` captura cualquier segmento: las rutas nuevas deben ir antes.
- `backend/modules/sales/api/filters.py:36-88` — `parse_order_filters` valida fechas (`AAAA-MM-DD`) y rango.
- `backend/modules/accounting/api/urls.py:39` — períodos fiscales en `GET /api/accounting/fiscal-periods/`; frontend: `features/accounting/services/fiscal-periods-api.service.ts:14`.
- `backend/requirements/base.txt:5` — `openpyxl==3.1.5` ya está; **no hay librería PDF** en backend ni frontend (`window.print` solo en `proforma-print-page`). `data_import` ya genera/lee xlsx (`data_import/infrastructure/file_parsers.py`, `sales-import-api.service.ts:308` descarga con `responseType: 'blob'`).
- `frontend/panel_admin/src/assets/data/routes.json:95-135` — submenú de Ventas: Pedidos, Importar (adminOnly), Configuración; `app.routes.ts:217-241` — rutas `sales/*` con `moduleGuard` (`data: { module: 'sales' }`).
- `docs/design/design-system.md` §5 «Lista de solo lectura con filtros» (referencia `inventory/pages/movement-list`) y «Dashboard y reportes»; `features/sales/pages/order-list` ya muestra el período de cada pedido.

### Hipótesis / supuestos no confirmados
- «Finalizada» = estado `DELIVERED`; «pagada» = `payment_status = PAID`. Con esa definición el saldo de cada fila es `0.00`; la columna se mantiene porque se pidió (y por si cambia la definición).
- «Fecha inicio/fin» filtran por `order_date` (igual que la lista de pedidos).
- «Período fiscal» filtra por el período con que se numeró el pedido (`fiscal_period_id`).

### Módulos y dependencias relacionadas
Sales (backend y frontend); lectura de períodos de Accounting solo en el frontend (selector); nombres de cliente vía puerto existente de Customers.

### Implementaciones similares existentes
Lista de pedidos (`OrderListCreateView` + `OrderPagination`), reporte `income_expense_views.py`, descarga blob de `sales-import-api.service.ts`.

### Comportamiento actual
No existe reporte de ventas pagadas ni exportación a PDF/Excel de pedidos.

### Restricciones
`company_id` en toda consulta; dinero en `Decimal`; sin texto hardcodeado (i18n es/en/pt); avisar antes de instalar dependencias.

### Riesgos identificados
- PDF requiere una dependencia nueva (p. ej. `reportlab`): confirmar antes de instalar.
- Exportaciones sin paginar pueden ser grandes: tope de filas.
- Con Contabilidad deshabilitado no hay selector de períodos.

### Veredicto de complejidad
**NEEDS_PLAN** — endpoint de solo lectura nuevo y pantalla nueva sobre datos existentes, sin cambios de dominio ni migraciones; la única decisión técnica relevante es la librería PDF.

### Diseño requerido
**SI** — pantalla nueva con filtros, tabla paginada y acciones de exportación.

## Diseño
DDR-reporte-ingresos-por-venta-pantalla (docs/design/DDR-reporte-ingresos-por-venta-pantalla.md).

## Arquitectura
No aplica según veredicto.

## Plan
docs/plans/PLAN-2026-11-26-reporte-ingresos-por-venta.md (v1, COMPACTO, READY).

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
