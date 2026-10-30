# REV-2026-10-30-reportes-adaptar-modulos-activos-04: Reportes: el periodo efectivo del selector depende solo de la tarjeta de Ventas

**Status:** Closed (re-review ciclo 2, ea68dc4: verificado)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-30-reportes-adaptar-modulos-activos.md (v1)
**Spec reference:** UI-02, AC-07, AC-08
**Plan mode:** COMPLETO
**Suggested owner:** delivery-engineer

## Description
En `reports.component.html:18-19` `app-period-selector` recibe `[effective]` de `sales.state$`. Con Ventas deshabilitado esa consulta es `EMPTY`, el estado se queda en "loading" y el selector nunca muestra el periodo efectivo del servidor aunque Gastos esté activo y devuelva su propio `period`.

## Expected behavior
El periodo efectivo se toma de la primera fuente disponible (ventas o gastos).

## Actual behavior
Con Ventas off y Gastos on el selector no muestra el rango efectivo (las tarjetas de gastos sí muestran su periodo).

## Evidence
```
reports.component.html:18  <app-period-selector [effective]="(sales.state$ | async)?.data?.period ?? null" ...
reports.component.ts:   readonly sales = new RemoteResource(() => this.fromSales(() => this.api.sales(this.selection)));  // EMPTY si Ventas off
```
