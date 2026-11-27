# PLAN-2026-11-26-reportes-compras-pagadas-y-por-pagar (v1)

**Task:** TASK-reportes-compras-pagadas-y-por-pagar · **Modo:** COMPACTO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-reporte-ingresos-por-venta-pantalla (reutilizado) / Ninguno

## Objective
Agregar al módulo Compras los submenús «Compras pagadas» y «Compras por pagar», con los mismos filtros, paginación y exportación a PDF y Excel que los reportes de ventas.

# Specification
- **Expected behavior:** cada reporte muestra compras de la empresa, más recientes primero, paginadas, con columnas Compra, Proveedor, Total y Saldo (`total - pagos confirmados`) y los totales de Total y Saldo de todo el conjunto filtrado.
  - **Compras pagadas:** confirmadas con `payment_status = paid`.
  - **Compras por pagar:** confirmadas con `payment_status` `unpaid` o `partial`.
- **Acceptance criteria:**
  - AC-01: «pagadas» solo trae compras confirmadas y pagadas; «por pagar» solo confirmadas con saldo (impagas o parciales); ninguna incluye borradores, canceladas ni compras de otra empresa.
  - AC-02: fecha inicio/fin filtran por `purchase_date` inclusive (inicio > fin da 400 por parámetro).
  - AC-03: período fiscal filtra por el período de numeración de la compra; id mal formado da 400.
  - AC-04: respuesta paginada (`page_size` ≤ 100) con `totals` (`orders_count`, `total`, `balance`) del conjunto filtrado.
  - AC-05: Excel y PDF descargan todas las filas con los filtros vigentes, mismas columnas y totales; el título es «Compras pagadas» / «Compras por pagar»; tope de 5 000 filas (400).
  - AC-06: submenús «Compras pagadas» y «Compras por pagar» (es/en/pt) bajo Compras; la pantalla usa «Compra» y «Proveedor» como etiquetas y enlaza cada compra a su detalle.
  - AC-07: requiere módulo `purchases` y autenticación; nunca expone datos de otra empresa.
  - AC-08: los reportes «Ingresos por venta» y «Pedidos por cobrar» siguen comportándose igual (regresión).
- **Edge/error cases:** igual que ventas (sin selector de período sin Contabilidad, estados vacío/error/cargando, exportar deshabilitado sin filas).
- **Out of scope:** filtro por proveedor, antigüedad de deuda, pagar desde el reporte.

**Contrato API (aditivo, `required_modules = ('purchases',)`):** `GET /api/purchases/paid-report/` y `GET /api/purchases/payable-report/` (query `date_from`, `date_to`, `fiscal_period_id`, `page`, `page_size`) → `{count, next, previous, results:[{id, code, order_date, customer:{id,name}|null, total, balance}], totals:{orders_count,total,balance}}` (misma forma que los reportes de ventas; `code` = referencia de la compra, `customer` = proveedor, `order_date` = fecha de la compra); exportación `.../export/{xlsx|pdf}/`. Rutas antes de `<uuid:purchase_id>/`.

# Test Specification
- Backend (`purchases/tests/test_purchase_reports.py`): AC-01..AC-04, AC-07 y exportación (AC-05); regresión AC-08 con las suites de ventas existentes.
- Frontend: specs del servicio y de la pantalla para los cuatro tipos (AC-06/08), menú (`sidebar-menu.spec`), `i18n:check`.
- **E2E: NO** — solo lectura, cubierto por API y componente.

# Implementation Plan
- **Files affected:**
  - Backend: mover el generador de archivos a `shared/report_export.py` (título y filas genéricos; ventas lo importa de ahí); `purchases`: `PurchaseFilters.fiscal_period_id`, repositorio (`fiscal_period_id`, `totals()`), casos de uso `PaidPurchasesReport` y `PayablePurchasesReport` en `application/`, vistas y URLs (`api/purchase_report_views.py`, `purchase_urls.py`), pruebas.
  - Frontend: mover pantalla, servicio y modelo a `shared/` con un tipo de reporte (`paid`, `receivable`, `purchases-paid`, `purchases-payable`) que define endpoint, etiquetas y destino del enlace; rutas `purchases/reports/paid` y `purchases/reports/payable`, `routes.json`, i18n es/en/pt, specs.
- **Steps:** (1) mover `report_export` a `shared/` y ajustar ventas, con regresión; (2) backend de compras con pruebas (AC-01..05, 07); (3) mover y parametrizar el frontend sin cambiar ventas (AC-08); (4) rutas, menú e i18n de compras (AC-06); (5) pruebas, lint, `i18n:check`.
- **Risks / New dependencies:** ninguna dependencia nueva. El movimiento de archivos toca los reportes de ventas ya publicados: cubierto por AC-08.
