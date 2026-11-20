# REV-2026-11-20-importacion-en-segundo-plano-01: Doble envio concurrente con la misma clave responde 409

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-20-importacion-en-segundo-plano.md (v1)
**Spec reference:** AC-04
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Dos peticiones simultaneas de `execute` con la misma `idempotency_key` leen la corrida en `PREVIEWED`; la segunda espera el lock, su `UPDATE ... exclude(ACTIVE)` afecta 0 filas y lanza `import_not_runnable` (409).

## Expected behavior
Debe devolver la corrida ya encolada (202) si la clave coincide.

## Actual behavior
Responde 409 `import_not_runnable`. El caso secuencial funciona y el boton del frontend se bloquea con `executing`.

## Evidence
`repositories.py` `enqueue`: `if not updated: raise ImportRuleViolation(...)`. Sugerencia: ante `updated == 0`, releer la corrida y devolverla si la clave coincide.
