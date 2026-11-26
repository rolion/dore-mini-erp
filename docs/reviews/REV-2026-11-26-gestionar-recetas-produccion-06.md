# REV-2026-11-26-gestionar-recetas-produccion-06: El TASK describe mal el orden 404/400 del PUT

**Status:** Resolved
**Severity:** Low
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-11-26-gestionar-recetas-produccion.md (v1)
**Spec reference:** TASK ## Implementación
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
El TASK dice que `PUT` con id ajeno responde 404 antes de validar el cuerpo; `_values()` valida antes, así que un cuerpo inválido da 400 primero. Sin impacto de seguridad.

## Expected behavior
Texto y comportamiento alineados.

## Actual behavior
400 antes que 404 con cuerpo inválido.

## Evidence
`api/views.py` (`_values` se evalúa antes de `_run`).

## Resolution
Resolved (ciclo de correcciones 2026-11-26), pendiente de verificación por el Quality Gate ciclo 2.
