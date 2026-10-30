# REV-2026-10-30-reportes-adaptar-modulos-activos-03: EDGE-04: si ModulesService falla, isDisabled asume módulos apagados y el dashboard pide Pendientes según el servicio de módulos, sin prueba

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-30-reportes-adaptar-modulos-activos.md (v1)
**Spec reference:** EDGE-04, AC-08, UI-01
**Plan mode:** COMPLETO
**Suggested owner:** delivery-engineer

## Description
`ModulesService.request()` ante un error de carga deja `enabledKeys` = solo módulos base (`access`, `catalog`), por lo que `isDisabled('sales')` pasa a ser `true` (el comentario y EDGE-04 dicen que no se asume). El dashboard decide con `modules.isDisabled('sales')` si pide `pending` y si muestra "No disponible" en las dos tarjetas de pendientes, aunque `sources` de la API diga que Ventas está activo; en sentido inverso, con módulos desactualizados (Ventas apagado en otra pestaña) `pending` se pide y el 403 `module_disabled` activa el error.interceptor (expulsión a «Módulo no habilitado»). Los specs no cubren el caso de fallo de carga de módulos. Mitigación existente: el `moduleGuard` de `/dashboard` y `/reports` (`data.module: reporting`) redirige si la carga falló, por lo que solo es alcanzable tras una recarga fallida con la pantalla ya abierta.

## Expected behavior
Las tarjetas de pendientes se guían por `sources.sales` de la respuesta del dashboard (fuente de verdad del servidor) y existe una prueba del caso "fallo de carga de módulos".

## Actual behavior
`dashboard.component.ts:49-56` usa `ModulesService.isDisabled`; ningún spec simula `enabledKeys` solo-base.

## Evidence
```
modules.service.ts:51-52  catchError: this.modulesSubject.next(null); this.enabledSubject.next(new Set(BASE_MODULE_KEYS));   // BASE = [access, catalog]
dashboard.component.ts:49  readonly pending = new RemoteResource(() => (this.salesDisabled ? EMPTY : this.api.pending()));
grep EDGE-04|fallo de carga en features/reporting/**/*.spec.ts -> sin resultados
```
