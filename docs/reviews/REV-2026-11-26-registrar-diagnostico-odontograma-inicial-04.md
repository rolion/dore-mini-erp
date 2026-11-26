# REV-2026-11-26-registrar-diagnostico-odontograma-inicial-04: Casos borde del plan sin prueba automatizada y mensaje de archivado que habla de proformas

**Status:** Closed
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-26-registrar-diagnostico-odontograma-inicial.md (v1)
**Spec reference:** Edge cases del plan; Test Specification (Integration tests: «bloqueo de segundo borrador, 409 por confirmada, paciente archivado»); INV-12
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
1. Faltan pruebas para: cambio de dentición de un borrador con piezas que dejan de ser válidas (400 y borrador conservado), cliente inactivo (ver REV-01), concurrencia de confirmaciones (ver REV-03), amend desde una evaluación ya reemplazada (solo cubierto parcialmente en `test_odontogram_api.py:139`), `PUT`/`confirm`/`DELETE` de una evaluación de otro paciente, y los 404 de profesional ajeno en `PUT` (solo se prueba en `POST`).
2. Al estar el perfil archivado, la respuesta 409 reutiliza el mensaje de proformas: `PatientGate.require_active` → «Reactiva el perfil odontológico antes de trabajar con sus proformas.» (`adapters.py`), poco apropiado para evaluaciones.

## Expected behavior
Cada caso borde del plan tiene al menos una prueba; el mensaje de 409 habla de evaluaciones o es genérico.

## Actual behavior
Verificación manual en esta revisión (prueba temporal, borrada): cambio de dentición con pieza 54 en borrador mixto:
```
DENTITION CHANGE -> 400 b'{"findings":["Hallazgo 1: la pieza 54 no es válida para la dentición permanent."]}'
STILL THERE mixed
AMEND REPLACED -> 409
AMEND LATEST -> 201
```
El comportamiento es correcto, pero no lo protege ninguna prueba del repositorio.

## Evidence
`grep` de nombres de prueba en `test_odontogram_api.py` y `test_odontogram_domain.py` (no existe prueba de dentición cambiada ni de cliente inactivo).


## Verificación Quality Gate #2
Cerrado. Existen pruebas de cambio de dentición (400 y borrador conservado), cliente inactivo, profesional ajeno en PUT, concurrencia y mensaje de archivado sin la palabra proforma. Suite completa OK.
