# REV-2026-11-03-agendar-y-gestionar-citas-05: HEX escritos a mano en appointment-detail.component.scss

**Status:** Fixed (pendiente de reverificación en el próximo Quality Gate)
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-03-agendar-y-gestionar-citas.md (v1)
**Spec reference:** design-system.md §8 («No introduce HEX»)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El SCSS define $dark-surface #16192a, $dark-text #96a2b4, $dark-strong #fff para el tema oscuro. Replica agenda.component.scss (precedente aceptado tras PB-AGE-001), pero la checklist prohíbe HEX nuevos.

## Expected behavior
Usar variables existentes o registrar la excepción en design-system §10 (deuda visual).

## Actual behavior
Tres HEX duplicados (el archivo además empieza con BOM).

## Evidence
appointment-detail.component.scss lineas 1-3; mismo patrón en features/agenda/agenda.component.scss.

## Resolución
BOM eliminado y excepción registrada en `design-system.md` §10 (importar `skins/_dark.scss` emitiría CSS global).
