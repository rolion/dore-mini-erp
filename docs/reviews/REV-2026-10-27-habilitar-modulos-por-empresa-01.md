# REV-2026-10-27-habilitar-modulos-por-empresa-01: Carga duplicada de `GET /api/modules/` al abrir la app

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-27-habilitar-modulos-por-empresa.md (v1)
**Spec reference:** EDGE-05, ADR punto 6 (una sola consulta al iniciar la app autenticada)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-engineer

## Description
En una carga en frío con una URL de módulo (p. ej. `/sales/orders`), `moduleGuard` llama a `modules.loadQuietly().subscribe()` cuando `enabledKeysValue === null`, y `SidebarComponent.ngOnInit` llama también a `loadQuietly()`. No hay deduplicación (ni `shareReplay`/petición en vuelo), por lo que se emiten dos `GET /api/modules/`. Además, `ModuleListComponent.load()` vuelve a consultar siempre.

## Expected behavior
El ADR describe una consulta al iniciar la app autenticada y al cambiar un módulo.

## Actual behavior
Dos peticiones concurrentes en la carga en frío. Funcionalmente inocuo (sembrado idempotente, resultado idéntico).

## Evidence
Lectura de código (no verificado en navegador): `frontend/panel_admin/src/app/core/guard/module.guard.ts:21-23` y `frontend/panel_admin/src/app/layout/sidebar/sidebar.component.ts` (`ngOnInit`, `this.modulesService.loadQuietly()`). `ModulesService.load()` no comparte la petición en vuelo.
