# REV-2026-11-04-mejorar-ux-horarios-y-ausencias-03: En edición, pulsar el día ya seleccionado deja la casilla visualmente desmarcada

**Status:** Fixed (pendiente de nueva revisión)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-04-mejorar-ux-horarios-y-ausencias.md (v1)
**Spec reference:** AC-07
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Los chips de día usan `[checked]="...includes(i)"` y `(change)="toggleDay(i)"`; en edición `toggleDay` fuerza selección única (`setValue([day])`).

## Expected behavior
El día seleccionado permanece marcado al pulsarlo de nuevo (selección única).

## Actual behavior
El navegador desmarca la casilla al pulsarla; como la expresión `[checked]` sigue valiendo `true`, Angular no reescribe la propiedad del DOM y la casilla se ve desmarcada aunque el modelo conserva el día. El botón Guardar sigue habilitado, por lo que la interfaz no refleja el estado real.

## Evidence
Lectura de `toggleDay` en `agenda.component.ts` y del chip en `agenda.component.html`. Sin verificación en navegador. Sugerencia: usar `type=radio` en edición o forzar `$event.target.checked`.
