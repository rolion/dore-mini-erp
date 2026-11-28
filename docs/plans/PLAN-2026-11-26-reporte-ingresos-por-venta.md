# PLAN-2026-11-26-reporte-ingresos-por-venta (v1)

**Task:** TASK-reporte-ingresos-por-venta · **Modo:** COMPACTO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-reporte-ingresos-por-venta-pantalla / Ninguno

## Objective
Agregar en Ventas el submenú «Ingresos por venta»: lista paginada de pedidos entregados y pagados, filtrable por fecha inicio, fecha fin y período fiscal, exportable a PDF y Excel.

# Specification
- **Expected behavior:** el reporte muestra pedidos de la empresa con `status = DELIVERED` y `payment_status = PAID`; sin filtros trae todos hasta la fecha, más recientes primero, paginados. Columnas: Pedido (código), Cliente, Total, Saldo (`total - paid_total`). Los totales de Total y Saldo cubren todo el conjunto filtrado.
- **Acceptance criteria:**
  - AC-01: solo aparecen pedidos entregados y pagados de la empresa del usuario; cancelados, devueltos, pendientes y parciales no.
  - AC-02: «Fecha inicio»/«Fecha fin» filtran por `order_date` (inclusive); inicio > fin responde 400 por parámetro.
  - AC-03: «Período fiscal» filtra por el período con que se numeró el pedido; un id inexistente o mal formado da 400.
  - AC-04: la respuesta está paginada (`page`, `page_size` ≤ 100) e incluye totales del conjunto filtrado.
  - AC-05: «Exportar Excel» y «Exportar PDF» descargan archivos con los filtros vigentes, todas las filas, las mismas columnas y los totales.
  - AC-06: el submenú «Ingresos por venta» aparece bajo Ventas (es/en/pt) y abre la pantalla del DDR con sus estados.
  - AC-07: requiere módulo `sales` habilitado y autenticación; nunca expone datos de otra empresa.
- **Edge/error cases:** sin resultados → «Sin registros» y exportar deshabilitado; Clientes deshabilitado → cliente «—»; exportación de más de 5 000 filas → 400 pidiendo acotar los filtros (tope técnico); Contabilidad deshabilitado → sin selector de período.
- **Out of scope:** pagos por fecha de cobro, filtros por cliente/canal, gráficos, cambios de dominio o migraciones, otros reportes.

**Contrato API (aditivo, `required_modules = ('sales',)`):**
- `GET /api/sales/orders/paid-report/?date_from&date_to&fiscal_period_id&page&page_size` → `{count, next, previous, results:[{id, code, customer:{id,name}|null, total, balance}], totals:{orders_count, total, balance}}` (importes como texto decimal).
- `GET /api/sales/orders/paid-report/export/xlsx/` y `.../export/pdf/` con los mismos filtros → archivo adjunto.
- Las rutas van antes de `<str:order_id>/` en `api/urls.py`.

# Test Specification
- Unit/integración backend (`modules/sales/tests/test_paid_report.py`): AC-01 (mezcla de estados y de empresas), AC-02, AC-03, AC-04, AC-07 (401/403 sin módulo/empresa); export: AC-05 (xlsx se abre con openpyxl y contiene filas y totales; pdf responde `application/pdf` con cabecera `%PDF`, y el tope de filas).
- Frontend (Karma): servicio de API (parámetros y blob), componente con `provideTestTranslations()` (AC-06: estados cargando/vacío/error, filtros, botones de exportar), prueba de claves i18n y de `routes.json` (menú).
- **E2E: NO** — reporte de solo lectura cubierto por pruebas de API y de componente.

# Implementation Plan
- **Files affected:**
  - Backend: `modules/sales/domain/repositories.py` (`fiscal_period_id` en `OrderFilters`), `infrastructure/django/repositories.py` (filtro), `application/queries.py` (`PaidOrdersReport`), `api/{filters,serializers,views,urls}.py`, nuevo `api/report_export.py` (xlsx/pdf), `requirements/base.txt`.
  - Frontend: `features/sales/pages/paid-report/`, servicio y modelo en `features/sales/`, `app.routes.ts` (`sales/reports/income`), `assets/data/routes.json`, `assets/i18n/{es,en,pt}.json`, specs; `design-system.md` §5/§6 una línea.
- **Steps:**
  1. Backend: filtro por período en `OrderFilters` y repositorio; caso de uso con estado/pago fijos y totales (AC-01..04).
  2. Endpoint de lista + serializer + pruebas (AC-01..04, AC-07).
  3. Exportación Excel con `openpyxl` y PDF; endpoints y pruebas (AC-05).
  4. Frontend: servicio, pantalla, ruta, menú e i18n (AC-06).
  5. Pruebas de frontend, lint (`ruff`/`flake8` en lo cambiado, `npm run lint`, `npm run i18n:check`).
- **Risks / New dependencies:** PDF necesita una librería nueva (propuesta: `reportlab`, a añadir en `requirements/base.txt`); **requiere confirmación antes de instalar** (`CLAUDE.md`). Si no se aprueba, alternativa: `fpdf2`.
