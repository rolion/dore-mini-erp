# TASK-reporte-pedidos-por-cobrar: Reporte «Pedidos por cobrar»

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** NO
**Rama:** task/TASK-reporte-pedidos-por-cobrar
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/130

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-26 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-11-26 | INVESTIGATION → PLANNING → ENGINEERING | NEEDS_PLAN, sin DDR; PLAN v1 READY, PR abierto | delivery-start |
| 2026-11-26 | ENGINEERING → REVIEW | Implementación completa | delivery-build |

## Investigación

### Requerimiento
«Genera un reporte similar [a Ingresos por venta] pero para pedidos por cobrar.» Mismo patrón: submenú de Ventas, filtros de fecha inicio, fecha fin y período fiscal, paginado, exportable a PDF y Excel, columnas Pedido, Cliente, Total y Saldo.

### Hechos encontrados
- `backend/modules/sales/application/queries.py` (`PaidOrdersReport`) y `api/views.py` (`PaidOrdersReportView`, `PaidOrdersReportExportView`), `api/report_export.py`, `api/urls.py`: reporte «Ingresos por venta» ya en `main` (PR #129), con filtros por fecha y `fiscal_period_id`, totales del conjunto y exportación xlsx/pdf (tope 5 000 filas).
- `docs/adr/ADR-ciclo-pedido-entrega-cobro-contrato-api.md:40` — «por cobrar» = `total > paid_total` (`has_balance=true`) y estado distinto de CANCELLED.
- `backend/modules/sales/infrastructure/django/read_queries.py:80-81` — `pending_collection`: pedidos válidos (ni cancelados ni devueltos) con `total > paid_total`.
- `frontend/panel_admin/src/app/features/sales/pages/paid-report/` — pantalla, servicio (`paid-report-api.service.ts`) y modelo del reporte actual; ruta `sales/reports/income` en `app.routes.ts`; menú en `assets/data/routes.json`; textos en `SALES.PAID_REPORT.*`.

### Hipótesis / supuestos no confirmados
- «Por cobrar» = pedidos no cancelados ni devueltos con saldo > 0, en cualquier estado de entrega (incluye los anticipos pendientes de pedidos aún no entregados), igual que el criterio ya usado en el tablero.
- Las fechas filtran por fecha del pedido y el período por el período con que se numeró el pedido (igual que el otro reporte). Los pedidos aún sin confirmar no tienen período, así que con un período seleccionado no aparecen.

### Restricciones y riesgos
`company_id` en todo; dinero en `Decimal`; sin texto hardcodeado; nombres de cliente neutralizados en Excel y PDF (ya resuelto en `report_export.py`). Riesgo: duplicar código; se resuelve parametrizando el reporte existente.

### Veredicto de complejidad
**NEEDS_PLAN** — endpoint de solo lectura aditivo sobre la misma infraestructura, sin migraciones ni dependencias nuevas.

### Diseño requerido
**NO** — misma pantalla y plantilla que `DDR-reporte-ingresos-por-venta-pantalla`; solo cambian título, subtítulo y texto vacío.

## Diseño
No aplica (reutiliza DDR-reporte-ingresos-por-venta-pantalla).

## Arquitectura
No aplica según veredicto.

## Plan
docs/plans/PLAN-2026-11-26-reporte-pedidos-por-cobrar.md (v1, COMPACTO, READY).

## Implementación
**Resumen.** Backend: base `_OrdersReport` con `PaidOrdersReport` y el nuevo `ReceivableOrdersReport` (no cancelados ni devueltos, `has_balance=True`); vistas de lista y exportación parametrizadas (`_OrdersReportView`, `_OrdersReportExportView`); `report_export` recibe el título; rutas `receivable-report/` y `receivable-report/export/{xlsx|pdf}/`. Frontend: la pantalla, el servicio y el modelo `paid-report` pasan a `sales-report` y se parametrizan por `kind` (`data.report` de la ruta); nueva ruta `sales/reports/receivable`, submenú «Pedidos por cobrar» e i18n es/en/pt (`SALES.RECEIVABLE_REPORT`).

**Cobertura.** AC-01..05 y AC-07: `test_receivable_report.py`; AC-06: `routes.json`, componente y `sidebar-menu.spec`; AC-08: `test_paid_report.py` y specs de ingresos siguen pasando tras el renombre.

**Desviaciones.** Ninguna respecto al plan. Los textos de los archivos exportados siguen solo en español (limitación heredada del reporte de ingresos).

**Verificación propia.** Backend: `test_receivable_report` + `test_paid_report` 19 OK; `ruff`/`flake8` sin avisos en lo nuevo. Frontend: specs del reporte y del menú 20 OK; `i18n:check` 0 faltantes.

## Review
_Pendiente_

## Publicación
_Pendiente_
