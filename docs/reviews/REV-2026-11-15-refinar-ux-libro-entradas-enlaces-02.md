# REV-2026-11-15-refinar-ux-libro-entradas-enlaces-02: Contraste de textos auxiliares sin medir

**Status:** Resolved
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

## Resolution
Parcialmente resuelto: el último `text-muted` migrado a `text-body-secondary`. El tema no sobrescribe `--bs-secondary-color` (Bootstrap 5.3): rgba(33,37,41,.75) sobre blanco ≈ 6,8:1 (claro) y rgba(222,226,230,.75) sobre #191d21 ≈ 9:1 (oscuro), calculado, no medido en navegador.

## Resolution
Medido en navegador (Chrome, app real contra API simulada): periodo y cobertura 6,78:1; aviso tenue 7,65:1; pie «3 en total» 4,59:1; enlaces azul Bootstrap 4,50:1 (en el límite). Tema oscuro no medido.
