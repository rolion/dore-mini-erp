# REV-2026-10-28-inventario-movimientos-trazables-01: npm run build falla: errores TS7053 en la plantilla de movement-list

**Status:** Resolved (pendiente de re-verificación por delivery-publish)
**Severity:** High
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-28-inventario-movimientos-trazables.md (v1)
**Spec reference:** UI-01 / AC-04 (la pantalla no compila para producción)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`ng build` (build de producción, plantillas con tipado estricto) rechaza `movement-list.component.html` porque `row` en las plantillas de `ngx-datatable` es `any` y se usa como índice de `Record<MovementKind,string>` / `Record<MovementStatus,string>`.

## Expected behavior
`npm run build` termina sin errores; la pantalla se puede desplegar.

## Actual behavior
`npm run build` termina con 3 errores `TS7053` (líneas 111, 113 y 116 de `movement-list.component.html`: `kindLabels[row.kind]` x2 y `statusLabels[row.status]`). `ng lint` y los specs Karma pasan porque no ejecutan la compilación estricta de plantillas del build de producción. El implementador solo declaró `tsc`, lint y Karma acotado; no ejecutó `npm run build`.

## Evidence
```
X [ERROR] TS7053: Element implicitly has an 'any' type because expression of type 'any' can't be used to index type 'Record<MovementKind, string>'.
    src/app/features/inventory/pages/movement-list/movement-list.component.html:111:73
    ...html:113:74  (Record<MovementKind,string>)
X [ERROR] TS7053 ... 'Record<MovementStatus, string>'.   ...html:116:77
```
Comando: `npm run build` desde `frontend/panel_admin/` (solo estos 3 errores, todos en archivos de este diff). Sugerencia: tipar la fila (`let-row="row"` con un getter/método `kindLabel(movement)` en el componente) en vez de indexar con `any`.
