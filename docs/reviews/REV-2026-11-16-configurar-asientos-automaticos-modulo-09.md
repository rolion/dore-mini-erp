# REV-2026-11-16-configurar-asientos-automaticos-modulo-09: La configuración de Gastos solo carga las primeras 100 categorías y puede declarar «Configuración completa» con categorías ocultas

**Status:** Resolved
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-16-configurar-asientos-automaticos-modulo.md (v3)
**Spec reference:** PLAN v3 (UI-01, EDGE-03, ExpenseSettingsComponent carga las categorías de Gastos), AC-12
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Tercera pasada. `ExpenseSettingsComponent.load()` llama `CategoriesApiService.list({ pageSize: 100 })` y usa solo `page.results`; ignora `page.next`. El backend limita `max_page_size = 100` (`backend/modules/expenses/api/pagination.py`). El TASK menciona «máx. 100» en una nota de implementación, pero ni la pantalla ni el panel avisan.

## Expected behavior
Todas las categorías de la empresa aparecen en «Cuenta de gasto por categoría» (o, si hay un tope deliberado, la pantalla lo dice). El estado «Configuración completa» y el aviso de faltantes cubren todas las categorías activas, porque el panel calcula `categoryIssues` solo a partir de las filas que recibe.

## Actual behavior
Con 104 categorías en la empresa (4 originales + 100 creadas por la API), `GET /api/expense-categories/?page_size=100` devuelve `count: 104`, 100 resultados y `next` no nulo; la pantalla `/es/pocketbiz/expenses/settings` muestra 100 filas (las 4 restantes no existen en la UI) y el aviso de faltantes lista 97 líneas. Las categorías 101+ no se pueden configurar desde el panel y, si las 100 visibles estuvieran configuradas, el panel mostraría «Configuración completa» aunque haya categorías activas sin cuenta (deducido del código: `complete` = `config.ready && !categoryIssues.length`, con `categoryIssues` solo de `categoryRows`). Además `expense-settings.component.spec.ts` solo prueba el caso feliz de 2 categorías (no hay prueba de error de carga ni de más de una página; el error y «Reintentar» sí funcionan en el navegador).

## Evidence
Navegador integrado, 1440x900, empresa de prueba con 104 categorías: filas `[data-testid^="row-category"]` = 100; `list.count` = 104, `returned` = 100, `next` = `...?page=2&page_size=100`. Corrección posible: seguir `next` hasta agotar páginas (p. ej. `expand`/`reduce` de RxJS) o avisar de forma visible cuando `next` no sea nulo; añadir spec.

## Resolution
`ExpenseSettingsComponent` carga todas las páginas de categorías (`expand` + `reduce`, 100 por página). Pruebas: paginación en dos páginas y error de carga con «Reintentar».
