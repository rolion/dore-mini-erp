# REV-2026-11-20-reporte-ingresos-egresos-contabilidad-02: `months` de otro período en la URL da error sin salida directa

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-20-reporte-ingresos-egresos-contabilidad.md (v1)
**Spec reference:** Edge cases (`months` fuera del período → 400)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Una URL con `months` que no pertenecen al período (editada a mano o enlace antiguo) devuelve 400; la UI muestra el error con «Reintentar», que no lo resuelve (solo «Limpiar filtros»).
## Expected behavior
El 400 es el comportamiento especificado; la UX podría ofrecer limpiar los filtros desde el error.
## Actual behavior
Error con «Reintentar» que repite la misma consulta.
## Evidence
Revisión de código del Quality Gate (`income-expense.component.html`, bloque `list-error`). No bloqueante.
