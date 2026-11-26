# TASK-reportes-compras-pagadas-y-por-pagar: Reportes «Compras pagadas» y «Compras por pagar»

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** NO
**Rama:** task/TASK-reportes-compras-pagadas-y-por-pagar
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/132

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-26 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-11-26 | INVESTIGATION → PLANNING → ENGINEERING | NEEDS_PLAN, sin DDR; PLAN v1 READY, PR abierto | delivery-start |
| 2026-11-26 | ENGINEERING → REVIEW | Implementación completa | delivery-build |

## Investigación

### Requerimiento
«Genera un reporte similar para compras. Necesitamos un reporte de compras pagadas y otro de compras por pagar.» «Similar» = el patrón de «Ingresos por venta» y «Pedidos por cobrar» (ya en `main`): submenú del módulo, filtros de fecha inicio, fecha fin y período fiscal, paginado, exportable a PDF y Excel, columnas documento, tercero, total y saldo.

### Hechos encontrados
- `backend/modules/purchases/domain/enums.py:4-19` — `PurchaseStatus` (draft/confirmed/cancelled) y `PaymentStatus` (unpaid/partial/paid); recepción y pago solo existen en compras confirmadas.
- `backend/modules/purchases/domain/repositories.py:15-48` — `PurchaseSummary` (`reference`, `supplier_name`, `total`, `paid_total`, `balance`) y `PurchaseFilters` (proveedor, fechas, estado, `payment_status`, `pending_payment` = unpaid o partial).
- `backend/modules/purchases/infrastructure/django/purchase_repository.py:100-144` — `list(...)` filtra por `company_id`, anota `paid_total` (suma de pagos confirmados) y aplica los filtros; no filtra por período fiscal ni calcula totales del conjunto.
- `backend/modules/purchases/infrastructure/django/models.py:43-45` — la compra guarda `fiscal_period_id` y `fiscal_period_name` al numerarse (las confirmadas siempre lo tienen).
- `backend/modules/purchases/api/purchase_urls.py` (montado en `/api/purchases/`), `purchase_views.py` (`REQUIRED_MODULES = ('purchases',)`, `SupplierPagination`), `purchase_filters.py`.
- Reportes de ventas ya hechos: `backend/modules/sales/api/views.py` (`_OrdersReportView`, `_OrdersReportExportView`), `report_export.py`, y frontend `features/sales/pages/sales-report` (componente parametrizado por tipo), `services/sales-report-api.service.ts`, `models/sales-report.ts`.
- `frontend/panel_admin/src/assets/data/routes.json` — submenú de Compras: Compras, Proveedores, Configuración; rutas `purchases/*` con `moduleGuard`.
- `CLAUDE.md`: lo que se necesite en un segundo módulo se mueve a `shared/`.

### Hipótesis / supuestos no confirmados
- «Compras pagadas» = compras **confirmadas** con `payment_status = paid`; «por pagar» = confirmadas con `unpaid` o `partial` (saldo > 0). Borradores y canceladas no entran en ninguno. Es independiente de si la mercadería ya se recibió.
- Fechas = `purchase_date`; período fiscal = el de la numeración de la compra (como en ventas).
- Columnas: Compra (referencia, p. ej. `NC-000012`), Proveedor, Total y Saldo. En «pagadas» el saldo siempre es 0.00 (como en ingresos por venta).

### Restricciones y riesgos
`company_id` en todo; dinero en `Decimal`; sin texto hardcodeado; neutralizar nombres en Excel/PDF (reutilizar `report_export`). Riesgo: dependencia entre módulos; el generador de archivos vive hoy en `sales/api`; se mueve a `shared/` (backend) para no importar entre módulos. Riesgo en frontend: la pantalla de reporte vive en `features/sales`; se mueve a `shared/` por la regla de `CLAUDE.md`.

### Veredicto de complejidad
**NEEDS_PLAN** — lecturas aditivas sobre estados existentes, sin migraciones ni dependencias nuevas; el trabajo relevante es mover a `shared/` lo reutilizable.

### Diseño requerido
**NO** — misma pantalla y plantilla que `DDR-reporte-ingresos-por-venta-pantalla`; cambian etiquetas (Compra/Proveedor), títulos y destino del enlace.

## Diseño
No aplica (reutiliza DDR-reporte-ingresos-por-venta-pantalla).

## Arquitectura
No aplica según veredicto.

## Plan
docs/plans/PLAN-2026-11-26-reportes-compras-pagadas-y-por-pagar.md (v1, COMPACTO, READY).

## Implementación
**Resumen.** Backend: el generador de archivos pasa de `sales/api/report_export.py` a `shared/report_export.py` (cabeceras y título parametrizables, `ReportTotals`); en `purchases`, `PurchaseFilters.fiscal_period_id`, `PurchaseRepository.totals()`, casos de uso `PaidPurchasesReport` / `PayablePurchasesReport` (`application/purchase_report_queries.py`) y vistas de lista y exportación (`api/purchase_report_views.py`) en `/api/purchases/paid-report/` y `/api/purchases/payable-report/`. Frontend: la pantalla, el servicio y el modelo de reporte pasan de `features/sales` a `shared/` (`DocumentReport*`), con una configuración por tipo (`paid`, `receivable`, `purchases-paid`, `purchases-payable`) que fija endpoint, textos, etiquetas de columna y enlace al detalle; rutas `purchases/reports/paid` y `purchases/reports/payable`, submenús de Compras e i18n es/en/pt.

**Cobertura.** AC-01..05 y AC-07: `purchases/tests/test_purchase_reports.py`; AC-06: rutas, `routes.json`, spec de la pantalla con el tipo de compras y `sidebar-menu.spec`; AC-08: `test_paid_report.py`, `test_receivable_report.py` y los specs de la pantalla para ventas siguen pasando tras el movimiento.

**Desviaciones.** El archivo de exportación de ventas conserva sus cabeceras («Pedido», «Cliente») pasándolas como parámetro. El movimiento a `shared/` fue necesario por la regla de `CLAUDE.md` (lo que usa un segundo módulo va a `shared/`).

**Verificación propia.** Backend: 27 pruebas de los tres reportes OK; `ruff`/`flake8` sin avisos nuevos. Frontend: specs de la pantalla, el servicio y el menú 22 OK; `i18n:check` 0 faltantes. Un error propio detectado por las pruebas: el reemplazo de `titleKey` dañó `subtitleKey` en la plantilla; corregido.

## Review
_Pendiente_

## Publicación
_Pendiente_
