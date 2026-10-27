# REV-2026-10-27-bloquear-api-modulos-deshabilitados-03: No hay caché por petición; la NFR «una consulta de módulos como máximo» no se cumple

**Status:** Resolved
**Severity:** Low
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-10-27-bloquear-api-modulos-deshabilitados.md (v1)
**Spec reference:** NFR («Una consulta de módulos por petición como máximo (caché por petición)»), ADR punto 4
**Plan mode:** COMPLETO
**Suggested owner:** delivery-engineer

## Description
El permiso llama a `module_gate.enabled_keys` y los adaptadores de Ventas/Reportes vuelven a llamar a `module_gate.is_enabled` (memoriza solo por instancia de adaptador). Resultado: 2 consultas de módulos en pedidos y reportes de pendientes/clientes (`test_list_does_not_query_per_row` pasó de 5 a 7). Además, una empresa que deshabilitó todos los módulos opcionales no tiene filas, así que `enabled_keys()` ejecuta `get_or_create` dentro de `atomic` en cada petición (3 consultas).

## Expected behavior
Una caché por petición según ADR/NFR, o la NFR reformulada.

## Actual behavior
La TASK documenta el costo (5→7) pero el ADR sigue afirmando una caché por petición que no existe. Impacto de rendimiento aceptado por el solicitante; sin riesgo de seguridad (no hay caché entre peticiones, AC-04 se cumple).

## Evidence
`backend/config/permissions.py:33`, `backend/modules/sales/infrastructure/adapters.py` y `backend/modules/reporting/infrastructure/adapters.py` (`is_available`), `backend/modules/modularity/infrastructure/django/repositories.py` (`enabled_keys`), `backend/modules/sales/tests/test_api.py` (assertNumQueries(7)). Corregir el texto del ADR/NFR o cachear en el request.
