# REV-2026-11-03-agendar-y-gestionar-citas-14: `loadCalendar` no participa del control de consultas (`requestId`) de la lista

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-03-agendar-y-gestionar-citas.md (v1)
**Spec reference:** AC-09 (estados cargando/vacío/error/éxito); REV-11
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Tras REV-11, `search()` protege `loading`, `rows` y `error` con `requestId`, pero `loadCalendar()` no lo incrementa y su `finalize` pone `loading = false` sin condición. Al cambiar de vista con una consulta en vuelo, la respuesta o el cierre de la otra consulta pisa el estado de la vista vigente.

## Expected behavior
Cambiar de vista con una carga en curso mantiene «Cargando…» hasta que termine la consulta de la vista activa y no muestra errores ni datos de la otra vista.

## Actual behavior
Por revisión de código (no reproducido en el navegador): (a) calendario en carga → pulsar «Listado»: el `finalize` del calendario apaga `loading` mientras la lista aún carga; (b) lista en carga → pulsar «Calendario»: la respuesta de la lista (aún considerada vigente porque `loadCalendar` no incrementa `requestId`) escribe `rows`/`count` o, si falla, `error` con el mensaje de la lista dentro de la vista de calendario. Es una condición ya existente antes del arreglo de REV-11, de efecto visual breve y se corrige sola al terminar las peticiones.

## Evidence
`frontend/panel_admin/src/app/features/agenda/pages/appointment-list.component.ts`: `loadCalendar` (`finalize(() => this.loading = false)`, sin `requestId`) y `search` (`if (requestId === this.requestId)`). Opción: incrementar `requestId` también en `loadCalendar` y condicionar su `finalize`/`error`.
