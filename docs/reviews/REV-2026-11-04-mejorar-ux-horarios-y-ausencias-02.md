# REV-2026-11-04-mejorar-ux-horarios-y-ausencias-02: Fechas escritas en inputs cuyo `type` aún no cambió pueden quedar vacías al alternar «Todo el día» o editar una ausencia de día completo

**Status:** Fixed (pendiente de nueva revisión)
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-04-mejorar-ux-horarios-y-ausencias.md (v1)
**Spec reference:** AC-10, UI del DDR (ausencia «Todo el día»)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Los inputs de ausencia cambian entre `datetime-local` y `date` con `[type]` según `allDay`; `toggleAllDay()` y `editAbsence()` escriben el valor con `patchValue`/`reset`.

## Expected behavior
Al activar/desactivar «Todo el día» o abrir la edición de una ausencia de días completos, los campos muestran las fechas correspondientes.

## Actual behavior
`patchValue`/`reset` ejecutan `writeValue` (`el.value = ...`) de forma síncrona, antes de la detección de cambios que actualiza `[type]`. Asignar `2026-11-05` a un `input[type=datetime-local]` (o `2026-11-05T00:00` a uno `type=date`) se sanea a cadena vacía y el cambio posterior de `type` no vuelve a escribir el valor. Resultado probable: el control tiene valor pero los campos se ven vacíos (y al editar una ausencia de día completo, AC-10, el diálogo se abriría con fechas en blanco). NO VERIFICADO en navegador (no se levantó la app).

## Evidence
Lectura de `agenda.component.ts` (`toggleAllDay`, `editAbsence`) y `agenda.component.html` (`[type]="absence.controls.allDay.value ? 'date' : 'datetime-local'"`). `agenda.component.spec.ts` solo prueba el modelo del formulario, no el valor del DOM. Verificar en navegador; si se confirma, escribir los valores tras la actualización del `type` (p. ej. dos inputs con `@if`) y añadir prueba de DOM.
