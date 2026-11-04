# REV-2026-11-03-agendar-y-gestionar-citas-12: Al abrir el calendario se borran los filtros del listado de la URL

**Status:** Open
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-03-agendar-y-gestionar-citas.md (v1)
**Spec reference:** DDR Pantallas («Filtros en la URL»); REV-02 / REV-09
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`syncUrl` en modo calendario pone a `null` los parámetros `from`, `to`, `professional`, `status` y `search` del listado (y la página). Los filtros siguen en el formulario de la sesión, pero ya no están en la URL.

## Expected behavior
Cambiar de vista no hace perder los filtros del listado al recargar o compartir (o se documenta que la vista de calendario los descarta).

## Actual behavior
En el navegador: desde `?from=2026-11-09&to=2026-11-09` al pulsar «Calendario» la URL pasó a `?view=calendar&cal_date=…&cal_span=1`. Si se recarga en esa vista y se vuelve a «Listado», los filtros anteriores se pierden (la sesión sin recargar sí los conserva). Impacto bajo: solo afecta a recargar o compartir en medio de un cambio de vista.

## Evidence
`appointment-list.component.ts`, `syncUrl`: `queryParams[key] = inList ? value || null : null` para cada filtro. Verificado en el navegador con el flujo anterior.
