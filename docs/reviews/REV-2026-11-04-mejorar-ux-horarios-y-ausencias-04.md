# REV-2026-11-04-mejorar-ux-horarios-y-ausencias-04: Elegir «Solo esta semana»/«Hasta fin de mes» al editar un turno reemplaza `valid_from` por el lunes visible

**Status:** Fixed (pendiente de nueva revisión)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-04-mejorar-ux-horarios-y-ausencias.md (v1)
**Spec reference:** DDR (Edición de un turno), AC-08
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
En edición los radios de repetición están disponibles y `applyRepeat()` hace `patchValue({ valid_from: this.start, valid_until })`.

## Expected behavior
La spec debería definir si, al editar, cambiar la repetición modifica también `valid_from` o solo `valid_until`.

## Actual behavior
Un turno vigente desde `2026-10-01` que se edita desde una semana posterior y al que se aplica «Hasta fin de mes» pasa a valer desde el lunes visible, recortando la cobertura previa (y la disponibilidad ya ofrecida) sin aviso. El DDR dice «vigencia con las mismas opciones» sin precisar este efecto. Comportamiento consistente con el plan, pero de riesgo de datos.

## Evidence
`agenda.component.ts` `applyRepeat()`; PLAN v1 «Edición de turno» no lo especifica. Decisión de negocio: aclarar en la spec.
