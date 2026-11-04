# REV-2026-11-03-agendar-y-gestionar-citas-03: El historial muestra «Usuario N» en lugar del autor

**Status:** Verified
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

## Resolución
El evento guarda `author_name` (migración `0003`) y la UI lo muestra. Cubierto en `test_appointments.py` y `appointment-detail.component.spec.ts`.

## Verificación (Quality Gate 2)
Verificado en gate 2: author_name en AppointmentEvent (migración 0003) y la UI lo muestra; en navegador el historial muestra 'visual'; test_appointments.py comprueba author_name.
