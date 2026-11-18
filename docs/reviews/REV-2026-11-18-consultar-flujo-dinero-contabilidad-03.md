# REV-2026-11-18-consultar-flujo-dinero-contabilidad-03: Paginación en memoria contradice el requisito no funcional de la Specification

**Status:** Open
**Severity:** Medium
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-11-18-consultar-flujo-dinero-contabilidad.md (v1)
**Spec reference:** NFR: «Agregación y paginación en la base de datos (sin traer todas las líneas a memoria para listar)»
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
La desviación declarada en `## Implementación` (paginación en memoria: `ListCashFlowMovements` carga todas las líneas del rango, clasifica y ordena en Python; la vista hace `list(result.movements)` y pagina) contradice el NFR de la Specification. Además no pasó por aprobación del usuario ni se registró como cambio de Specification/PLAN.

## Expected behavior
O se cumple el NFR, o se enmienda la Specification (con aprobación del usuario) aceptando la agregación por asiento en memoria con un tope/riesgo explícito para rangos grandes.

## Actual behavior
Con rangos grandes se traen a memoria todas las líneas de dinero (agregadas por asiento y cuenta en BD) y todas las filas clasificadas antes de paginar. No es incorrecto funcionalmente; es una desviación no autorizada de un NFR. La deuda sí está documentada (TASK ## Implementación).

## Evidence
`backend/modules/accounting/application/cash_flow.py` (`ListCashFlowMovements.execute`) y `api/cash_flow_views.py` (`paginate_queryset(list(result.movements), ...)`). Las tablas Bootstrap simples en lugar de ngx-datatable sí son coherentes con el DDR.
