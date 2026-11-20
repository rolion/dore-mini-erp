# REV-2026-11-20-reporte-ingresos-egresos-contabilidad-03: Tabla ilegible en móvil (ancho mínimo global de 800 px)

**Status:** Fixed
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-20-reporte-ingresos-egresos-contabilidad.md (v1)
**Spec reference:** UI-01, UI-02 (DDR: «Móvil: tabla con `table-responsive`»)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Revisión visual en el navegador integrado (375 px): la regla global `.table-responsive table { min-width: 800px }` (`assets/scss/override/_table.scss:557`) dejaba visible solo la columna Mes; Ingreso, Egreso y Utilidad quedaban tras un desplazamiento horizontal.
## Expected behavior
Las cuatro columnas se leen sin desplazamiento horizontal a 375 px.
## Actual behavior
Tabla de 800 px en un contenedor de 279 px.
## Evidence
Medición en el navegador: `clientWidth 279 / scrollWidth 800`. Corregido con `income-expense.component.scss` (sin ancho mínimo, fuente y relleno compactos bajo 576 px, «(pérdida)» en su propia línea) y márgenes laterales nulos en móvil; tras el cambio `295 / 295` (sin desplazamiento).
