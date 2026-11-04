# REV-2026-11-04-mejorar-ux-horarios-y-ausencias-01: `days` con elementos no hashables responde 500 en lugar de 400

**Status:** Fixed (pendiente de nueva revisión)
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-04-mejorar-ux-horarios-y-ausencias.md (v1)
**Spec reference:** INV-04, EDGE-02, AC-03
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`ShiftView.multiple_days` valida la lista de días.

## Expected behavior
Cualquier `days` que no sea una lista de enteros válidos responde 400 (EDGE-02), sin importar el contenido de la lista.

## Actual behavior
En `backend/modules/agenda/api.py` (`multiple_days`) la condición evalúa `len(set(days)) != len(days)` antes de comprobar el tipo de cada elemento. Con `days: [[1]]` o `days: [{}]` `set()` lanza `TypeError: unhashable type` y DRF responde 500. La prueba `test_invalid_days_are_rejected` no cubre estos casos (solo `[]`, `[7]`, `[-1]`, `[1,1]`, `['1']`, `'x'`, `[True]`).

## Evidence
Lectura de `git diff origin/main...HEAD -- backend/modules/agenda/api.py`: la expresión `not isinstance(days, list) or not days or len(set(days)) != len(days) or any(type(day) is not int ...)`. Las pruebas de backend NO se ejecutaron (sin DATABASE_URL); hallazgo por análisis estático. Sugerencia: validar primero el tipo de cada elemento y añadir `[[1]]`, `[{}]`, `[null]` a la prueba.
