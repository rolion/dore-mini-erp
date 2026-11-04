# REV-2026-11-04-cobrar-servicios-anticipos-pagos-parciales-03: La lista de Cobros captura `Exception` genérica al filtrar por permisos

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-04-cobrar-servicios-anticipos-pagos-parciales.md (v1)
**Spec reference:** AC-10 / Authorization
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`ObligationListView.get` descarta filas con `except Exception: continue` al evaluar `_authorize` por fuente. Solo se esperan `NotFound` y `PermissionDenied`; cualquier otro error (p. ej. de base de datos) se silencia y la lista sale incompleta sin rastro. Además `_authorize` se reejecuta por fila en lugar de una vez por tipo de fuente.

## Expected behavior
Capturar solo `NotFound`/`PermissionDenied` y evaluar el permiso una vez por `kind`.

## Actual behavior
Errores inesperados quedan ocultos y se pierden filas silenciosamente; coste por fila innecesario.

## Evidence
bandit -r modules/receivables: >> Issue: [B112:try_except_continue] Severity: Low Confidence: High, Location: modules/receivables\api\views.py:118:12
