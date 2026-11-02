# REV-2026-11-02-administrar-catalogo-servicios-02: Recuperar página tras desactivar último registro

**Status:** Closed
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
Cerrado por segunda revisión independiente sobre 3e932c3: corrección confirmada, sin defectos nuevos.

## Segunda revisión focal (3e932c3)
Revisor independiente confirmó REV-01 y REV-02 corregidos. Ejecutó `manage.py test modules.service_catalog.tests.test_pagination --settings=config.settings.test` con PostgreSQL solo como configuración de motor, sin conexión requerida por SimpleTestCase:
```text
..
Ran 2 tests in 0.002s
OK
Found 2 test(s).
System check identified no issues (0 silenced).
```
REV-02 se confirmó por lectura de código y regresiones; Angular fue ejecutado por el implementador (20 tests OK), no por el revisor focal. Cerrar estos hallazgos no equivale a PASS global: API/BD/concurrencia y revisión visual integrada continúan sin verificar.
