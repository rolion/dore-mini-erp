# REV-2026-11-04-mejorar-ux-horarios-y-ausencias-05: Accesibilidad: grupo de chips sin `aria-label` y acciones «Editar»/«Eliminar» repetidas sin contexto

**Status:** Fixed (pendiente de nueva revisión)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-04-mejorar-ux-horarios-y-ausencias.md (v1)
**Spec reference:** DDR (chips con `role="group"` y `aria-label`), design-system secciones 7 y 8
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El grupo de chips usa `role="group"` sin nombre y cada ausencia repite los enlaces «Editar» y «Eliminar» con el mismo texto.

## Expected behavior
El grupo de chips tiene `aria-label` (lo exige el DDR) y las acciones por ausencia son distinguibles para lector de pantalla (p. ej. `aria-label` con el motivo).

## Actual behavior
`<div class="d-flex flex-wrap gap-1 mb-1" role="group">` no tiene nombre accesible (ya está dentro de un `fieldset` con `legend`, por lo que el rol es redundante). Los botones «Editar»/«Eliminar» de cada ausencia, y «Copiar a otros días» por turno, no incluyen el contexto del renglón.

## Evidence
Lectura de `agenda.component.html`. Sin HEX ni estilos en línea (`grep` sin coincidencias); botones conformes a sección 3 (una acción `btn-primary` por bloque, `btn-light` para cancelar). Revisión visual en navegador: NO VERIFICADA.
