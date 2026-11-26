# PLAN-2026-11-26-reporte-pedidos-por-cobrar (v1)

**Task:** TASK-reporte-pedidos-por-cobrar · **Modo:** COMPACTO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-reporte-ingresos-por-venta-pantalla (reutilizado) / Ninguno

## Objective
Agregar el submenú «Pedidos por cobrar» en Ventas: pedidos con saldo pendiente, con los mismos filtros, paginación y exportación a PDF y Excel que «Ingresos por venta».

# Specification
- **Expected behavior:** el reporte muestra pedidos de la empresa que no están cancelados ni devueltos y tienen `total > paid_total`; sin filtros trae todos hasta la fecha, más recientes primero, paginados. Columnas: Pedido, Cliente, Total, Saldo (`total - paid_total`); los totales de Total y Saldo cubren todo el conjunto filtrado.
- **Acceptance criteria:**
  - AC-01: solo aparecen pedidos de la empresa con saldo > 0 y estado distinto de cancelado y devuelto (entregados o no); los pagados por completo no.
  - AC-02: fecha inicio/fin filtran por `order_date` inclusive (inicio > fin da 400 por parámetro).
  - AC-03: período fiscal filtra por el período con que se numeró el pedido; id mal formado da 400.
  - AC-04: respuesta paginada (`page_size` ≤ 100) con `totals` del conjunto filtrado.
  - AC-05: «Exportar Excel» y «Exportar PDF» descargan todas las filas con los filtros vigentes, mismas columnas y totales; el título del archivo es «Pedidos por cobrar».
  - AC-06: el submenú «Pedidos por cobrar» (es/en/pt) aparece bajo Ventas, después de «Ingresos por venta», y abre la pantalla con sus propios título, subtítulo y vacío.
  - AC-07: requiere módulo `sales` y autenticación; nunca expone datos de otra empresa.
  - AC-08: «Ingresos por venta» se comporta exactamente igual que antes (regresión).
- **Edge/error cases:** igual que el reporte de ingresos (tope de 5 000 filas, Clientes deshabilitado, sin selector de período sin Contabilidad).
- **Out of scope:** antigüedad de saldos, filtro por cliente, registrar cobros desde el reporte.

**Contrato API (aditivo):** `GET /api/orders/receivable-report/` (mismos parámetros y forma que `paid-report/`) y `GET /api/orders/receivable-report/export/{xlsx|pdf}/`; rutas antes de `<str:order_id>/`.

# Test Specification
- Backend (`test_receivable_report.py`): AC-01..AC-04, AC-07 y exportación (AC-05, incluido el título); `test_paid_report.py` existente cubre AC-08.
- Frontend: specs del servicio y del componente parametrizados por tipo de reporte (AC-05/06/08), menú (`sidebar-menu.spec`), `i18n:check`.
- **E2E: NO** — solo lectura, cubierto por API y componente.

# Implementation Plan
- **Files affected:** backend `application/queries.py` (`ReceivableOrdersReport`), `api/views.py` (vistas parametrizadas por reporte), `api/report_export.py` (título como parámetro), `api/urls.py`; frontend: renombrar la pantalla/servicio/modelo `paid-report` a `sales-report` parametrizados por `kind` (`paid` | `receivable`) vía datos de la ruta, nueva ruta `sales/reports/receivable`, `routes.json`, i18n es/en/pt, specs.
- **Steps:** (1) backend caso de uso + vistas + export con título + pruebas (AC-01..05, 07, 08); (2) frontend parametrizado + ruta + menú + i18n (AC-06); (3) pruebas, lint, i18n:check.
- **Risks / New dependencies:** ninguna dependencia nueva. El renombre toca archivos del reporte anterior: la regresión AC-08 lo cubre.
