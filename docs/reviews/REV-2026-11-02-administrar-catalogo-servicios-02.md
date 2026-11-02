# REV-2026-11-02-administrar-catalogo-servicios-02: Recuperar página tras desactivar último registro

**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-02-administrar-catalogo-servicios.md (v2)
**Spec reference:** AC-08 / UI-01
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Quality Gate independiente sobre 2e44a87 detectó que desactivar el único servicio de la última página filtrada podía dejar una página inexistente. Reintentar repetía la misma petición sin recuperación.
## Expected behavior
Tras reducir el conjunto, recuperar una página válida conservando búsqueda y estado. Otros errores siguen visibles y reintentables.
## Actual behavior
En 2e44a87 la recuperación a primera página solo se hacía ante respuesta exitosa vacía; DRF devolvía error en vez de esa respuesta. Detectado estáticamente, recorrido integrado pendiente.
## Evidence
`frontend/panel_admin/src/app/features/services/pages/service-list.component.ts`, onUpdated/catchError en 2e44a87.

## Corrección delivery-build
ServiceApiError identifica error 400 del campo page; la lista reintenta una sola vez desde página 1 con los filtros actuales. Tests de adaptador HTTP y de desactivar último registro de página guardada. Los errores restantes mantienen mensaje/reintento y no se ocultan.
Pendiente de confirmar cierre en revisión independiente de la corrección.
