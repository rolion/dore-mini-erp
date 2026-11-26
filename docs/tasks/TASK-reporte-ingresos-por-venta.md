# TASK-reporte-ingresos-por-venta: Reporte «Ingresos por venta» (ventas entregadas y pagadas)

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** SI
**Rama:** task/TASK-reporte-ingresos-por-venta
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/129

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-26 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-11-26 | INVESTIGATION → DESIGN → PLANNING | Veredicto NEEDS_PLAN, diseño requerido; DDR y PLAN v1 | delivery-start |
| 2026-11-26 | PLANNING → ENGINEERING | Specification READY, PR abierto | delivery-start |
| 2026-11-26 | ENGINEERING → REVIEW | Implementación completa | delivery-build |

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
**Resumen.** Backend (sales): `OrderFilters.fiscal_period_id` + filtro en el repositorio y `totals()`; caso de uso `PaidOrdersReport` (fija DELIVERED + PAID); `GET /api/orders/paid-report/` (paginado, con `totals`) y `GET /api/orders/paid-report/export/{xlsx|pdf}/` (`api/report_export.py`, tope de 5 000 filas). Frontend: pantalla `features/sales/pages/paid-report`, servicio y modelo, ruta `sales/reports/income`, submenú «Ingresos por venta» e i18n es/en/pt.

**Cobertura.** AC-01..04 y AC-07: `PaidOrdersReport` + `test_paid_report.py`; AC-05: `report_export.py` y pruebas de exportación; AC-06: ruta, `routes.json`, componente y specs.

**Desviaciones.**
- La API real cuelga de `/api/orders/` (no `/api/sales/orders/`); el contrato del PLAN se aplicó con ese prefijo.
- Tabla simple `table-responsive` + `ngb-pagination` en lugar de `ngx-datatable` y sin la variante compacta con panel de filtros: los filtros son solo tres y caben apilados en móvil.
- `reportlab==4.2.5` añadido a `requirements/base.txt` (confirmado por el usuario).

**Verificación propia.** Frontend: `ng test` de los specs nuevos y de `sidebar-menu.spec` (17 de 17 OK); `npm run i18n:check` OK. Backend: `ruff`/`flake8` sin avisos nuevos y `manage.py check` OK, pero **las pruebas de `test_paid_report.py` no se pudieron ejecutar**: el worktree no tiene `backend/.env` ni `DATABASE_URL` y el proyecto prohíbe leer `.env`. Debe correrlas `delivery-publish` o la persona con su entorno.

**Deuda / notas.** `ng lint` no tiene `eslint.config` en el proyecto. La prueba de módulo deshabilitado (AC-07) parchea `shared.module_gate.is_enabled`; si el permiso importa la función por nombre habrá que ajustar el parche.

## Review
_Pendiente_

## Publicación
_Pendiente_
