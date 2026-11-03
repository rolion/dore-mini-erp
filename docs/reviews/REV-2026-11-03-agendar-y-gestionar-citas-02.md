# REV-2026-11-03-agendar-y-gestionar-citas-02: Los filtros del listado no se reflejan en la URL

**Status:** Open
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-03-agendar-y-gestionar-citas.md (v1)
**Spec reference:** DDR Pantallas («Filtros en la URL»)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El DDR indica que los filtros (fecha, profesional, estado, búsqueda) viven en la URL, como en purchase-list. AppointmentListComponent no usa ActivatedRoute ni queryParams.

## Expected behavior
Filtros y página recuperables al recargar o compartir el enlace.

## Actual behavior
Los filtros se pierden al recargar o volver desde el detalle.

## Evidence
grep ActivatedRoute|queryParam en appointment-list.component.*: sin coincidencias.
