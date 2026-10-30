# REV-2026-10-29-inventario-existencias-filtros-accesos-operativos-02: StockFiltersState no se reinicia al cerrar sesión

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-29-inventario-existencias-filtros-accesos-operativos.md (v1)
**Spec reference:** AC-08 (conservar filtros «mientras dure la sesión»), DDR «Consecuencias»
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`StockFiltersState` es un servicio `providedIn: 'root'` en memoria que guarda búsqueda, almacén, filtros y página. Su método `reset()` no se llama en ningún sitio; `AuthService.clearSession()` reinicia `modulesService` pero no este estado.

## Expected behavior
Los filtros solo se conservan durante la sesión de la persona; al cerrar sesión (o iniciar otra) se parte de los valores por defecto.

## Actual behavior
Si otra persona inicia sesión en la misma pestaña sin recargar, la lista de Existencias se abre con el texto de búsqueda y los filtros de la sesión anterior (el almacén guardado se descarta si no está en la lista de la nueva empresa, pero `search`, categoría y usos permanecen). No hay fuga de datos de negocio entre empresas (los datos siempre vienen del servidor), solo del texto de filtros.

## Evidence
- `grep` de `StockFiltersState`/`reset()`: sin usos fuera de `stock-list` y de la propia clase.
- `frontend/panel_admin/src/app/core/service/auth.service.ts` `clearSession()` (líneas ~98-102).
