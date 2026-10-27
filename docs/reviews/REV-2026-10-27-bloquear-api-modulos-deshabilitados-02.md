# REV-2026-10-27-bloquear-api-modulos-deshabilitados-02: EDGE-05 lanza `GateNotConfigured`, no `ImproperlyConfigured`

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-27-bloquear-api-modulos-deshabilitados.md (v1)
**Spec reference:** EDGE-05
**Plan mode:** COMPLETO
**Suggested owner:** delivery-engineer

## Description
EDGE-05 especifica `ImproperlyConfigured` cuando el proveedor de `module_gate` no está registrado. El código define `GateNotConfigured(Exception)` y el test lo comprueba; la desviación no está en la sección «Desviaciones» de la TASK.

## Expected behavior
`django.core.exceptions.ImproperlyConfigured` (o la desviación documentada).

## Actual behavior
`GateNotConfigured(Exception)`. Es fail-closed igualmente (error 500, nunca concede acceso), por eso es Low.

## Evidence
`backend/shared/module_gate.py` (clase `GateNotConfigured`, `enabled_keys`), `backend/modules/modularity/tests/test_gate.py:13-16`.
