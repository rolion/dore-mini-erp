# REV-2026-11-03-agendar-y-gestionar-citas-03: El historial muestra «Usuario N» en lugar del autor

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-03-agendar-y-gestionar-citas.md (v1)
**Spec reference:** TASK (reprogramar conserva horario anterior, autor y motivo); DDR Historial
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El historial guarda author_id y la UI imprime «Usuario {id}»; no hay nombre legible.

## Expected behavior
Autor identificable por la recepción (nombre de usuario).

## Actual behavior
Se muestra un identificador numérico.

## Evidence
appointment-detail.component.html: <td>Usuario {{ event.author_id }}</td>. El dato sí se guarda (AC-05 verificado en test_appointments.py).
