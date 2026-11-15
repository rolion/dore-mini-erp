# REV-2026-11-15-refinar-ux-libro-entradas-enlaces-02: Contraste de textos auxiliares sin medir

**Status:** Open
**Severity:** Medium
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-11-15-refinar-ux-libro-entradas-enlaces.md (v1)
**Spec reference:** AC-05
**Plan mode:** COMPACTO
**Suggested owner:** delivery-start

## Description
Contraste de textos auxiliares sin medir.

## Expected behavior
Contraste >= 4,5:1 con valores computados registrados.

## Actual behavior
Se cambió text-muted por text-body-secondary sin medición; `<small class="text-muted">` de «(módulo deshabilitado)» quedó sin migrar.

## Evidence
Sin medición en navegador (no se levantó la app). Declarado como desviación en el TASK; el aprobador humano decide si lo acepta o exige medir.
