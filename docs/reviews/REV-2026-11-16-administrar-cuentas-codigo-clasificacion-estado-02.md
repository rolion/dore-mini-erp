# REV-2026-11-16-administrar-cuentas-codigo-clasificacion-estado-02: Campos no se bloquean en el diálogo cuando hay asientos

**Status:** Closed
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-16-administrar-cuentas-codigo-clasificacion-estado.md (v1)
**Spec reference:** UI-02
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
UI-02 pide campos bloqueados cuando la cuenta tiene asientos. El API no expone si los hay y calcularlo por cuenta sería N+1, así que el diálogo confía en el 409 `account_has_entries` y lo muestra como aviso.

## Expected behavior
Clasificación y casilla correctora deshabilitadas de entrada.

## Actual behavior
Se habilitan y el servidor rechaza el cambio con un aviso visible. Desviación declarada en el TASK; la barrera real es el backend y está probada.

## Evidence
`## Implementación` del TASK, desviación 1. Mejora futura: campo `has_entries` en el listado (una consulta agregada). Informe del Quality Gate, hallazgo 2.

## Resolution
Corregido: `GET /api/accounting/accounts/` y el detalle devuelven `has_entries` (listado con una sola consulta, probado sin N+1) y el diálogo deshabilita la clasificación y la casilla correctora cuando es verdadero; sus valores se envían sin cambio y el 409 `account_has_entries` sigue siendo la barrera real. PLAN v4.
