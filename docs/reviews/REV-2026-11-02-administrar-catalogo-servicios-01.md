# REV-2026-11-02-administrar-catalogo-servicios-01: Validar paginación como error de campo

**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-02-administrar-catalogo-servicios.md (v2)
**Spec reference:** API contract: parámetros inválidos 400
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Quality Gate independiente sobre 2e44a87 identificó que PageNumberPagination devolvía 404 para página inexistente y usaba tamaño predeterminado ante page_size inválido.
## Expected behavior
400 por campo para parámetros de paginación inválidos o página no disponible, conforme al contrato del PLAN.
## Actual behavior
En 2e44a87 se heredaban valores DRF sin validación adicional. Detectado por lectura; integración PostgreSQL no ejecutada.
## Evidence
`backend/modules/service_catalog/api/views.py`, ServicePagination en 2e44a87: solo page_size/page_size_query_param/max_page_size.

## Corrección delivery-build
Validar enteros ASCII positivos y longitud acotada; convertir NotFound de paginación a ValidationError de page. Pruebas SimpleTestCase sin BD para valores inválidos, longitud extrema, página inexistente, paginación válida y primera página vacía; prueba API PostgreSQL también añadida, pendiente de entorno.

Autoverificación posterior:
```text
Ran 23 tests in 1.749s
OK
Found 23 test(s).
System check identified no issues (0 silenced).
```
Pendiente de confirmar cierre en revisión independiente de la corrección.
