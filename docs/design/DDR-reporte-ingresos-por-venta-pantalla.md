# DDR-reporte-ingresos-por-venta-pantalla: Pantalla «Ingresos por venta»

**Estado:** Propuesto
**Task relacionado:** TASK-reporte-ingresos-por-venta
**Fecha:** 2026-11-26

## Contexto
Reporte de solo lectura de pedidos entregados y pagados, con filtros por fecha y período fiscal y exportación a PDF y Excel.

## Pantallas/flujos afectados
- Nueva: `/pocketbiz/sales/reports/income` («Ingresos por venta»), submenú de Ventas, después de «Pedidos».
- Menú: nueva entrada en `routes.json` (`MENUITEMS.SALES.LIST.INCOME_REPORT`).

## Componentes/patrones elegidos
Plantilla «Lista de solo lectura con filtros» (referencia `features/inventory/pages/movement-list`): breadcrumb, `.card`, filtros en fila (Fecha inicio, Fecha fin `input type=date`, Período fiscal `form-select`, «Limpiar filtros»), `ngx-datatable` con paginación del servidor, variante compacta < 992 px con `CompactViewportService`.
- Columnas: Pedido (código, enlace al detalle), Cliente («—» si no hay o Clientes está deshabilitado), Total y Saldo (`money`, a la derecha).
- Pie con «Totales» (suma de Total y Saldo del conjunto filtrado, no solo de la página).
- Botones «Exportar PDF» y «Exportar Excel» (`btn btn-outline-secondary`, iconos `fas`) en la cabecera de la tarjeta; descargan con los filtros vigentes, todas las filas, y se deshabilitan mientras descargan o si no hay filas.
- **Desviación aceptada (implementación):** tabla Bootstrap `table-responsive` con `ngb-pagination` en lugar de `ngx-datatable`, y sin la variante compacta con panel «Filtros»: son solo tres filtros, que se apilan en móvil, y una tabla de cuatro columnas se desplaza horizontalmente sin perder datos. Misma estructura (breadcrumb, `.card`, filtros en fila, resumen «Mostrando n–m de N»).

## Alternativas consideradas
Exportar solo la página visible (descartado: un reporte exportado debe ser completo); imprimir con `window.print` (descartado: no hay Excel y el formato depende del navegador).

## Comportamiento por privilegio/estado
- Estados: cargando, vacío («Sin registros»), error con «Reintentar», éxito. Selector de período: si Contabilidad está deshabilitado se oculta y el reporte filtra solo por fechas.
- Acceso por `moduleGuard` (`sales`). El backend exige el módulo `sales` y filtra por `company_id`; el frontend no es la barrera.

## Consecuencias
Un patrón de reporte tabular exportable nuevo; se documenta en `design-system.md` §5 si se reutiliza.
