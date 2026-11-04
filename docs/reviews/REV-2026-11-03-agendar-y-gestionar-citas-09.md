# REV-2026-11-03-agendar-y-gestionar-citas-09: Residuos en filtros en URL (vista del calendario y página fuera de rango)

**Status:** Verified
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-03-agendar-y-gestionar-citas.md (v1)
**Spec reference:** DDR Pantallas («Filtros en la URL»); resolución de REV-02 («Filtros, página y vista se leen de la URL»)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
1) La vista (Listado/Calendario) y los controles del calendario (profesional, fecha, diaria/semanal) no se escriben ni se leen de la URL, aunque la resolución de REV-02 dice que la vista sí. 2) Con `?page=99` (p. ej. un enlace viejo o un resultado que se redujo) el servidor responde 404, la pantalla muestra «No se pudieron cargar las citas» y «Reintentar» repite la misma página: queda atascada hasta pulsar «Filtrar» o «Limpiar filtros».

## Expected behavior
Vista y parámetros del calendario recuperables desde la URL (o la resolución ajustada), y una página fuera de rango vuelve a la última página válida o a la 1.

## Actual behavior
Al recargar en modo Calendario vuelve al Listado; `?page=99` queda en error con reintento inútil.

## Evidence
appointment-list.component.ts: ngOnInit lee from/to/professional/status/search/page, no `view`; `search(page)` se reintenta con la misma `page`; DRF PageNumberPagination responde 404 a páginas inexistentes. En navegador, tras «Ver agenda» el `location.search` quedó vacío.

## Resolución
La vista y los controles del calendario viajan en la URL (`view`, `cal_professional`, `cal_date`, `cal_span`) y se restauran al abrir; una página inexistente (404) vuelve a la 1. Specs en `appointment-list.component.spec.ts`.

## Verificación (Quality Gate 3)
Verificado en gate 3 en el navegador: «Calendario» escribe `?view=calendar&cal_date=…&cal_span=…`; tras elegir profesional y «Ver agenda» la URL queda `?view=calendar&cal_professional=<id>&cal_date=2026-11-09&cal_span=7`; recargar esa URL restaura la vista (Calendario pulsado, profesional, fecha y 7 secciones con las citas) y volver desde el detalle (`history back`) recupera el calendario. Sin bucle de navegación (`history.length` +1 por cada navegación explícita). `?page=99` responde 404, vuelve solo a la página 1 (URL limpia, «Página 1 de 1», 3 filas, sin alerta). Specs nuevos en `appointment-list.component.spec.ts` (Karma completo: 1139 correctas). Residuos menores en REV-2026-11-03-agendar-y-gestionar-citas-11 y -12.
