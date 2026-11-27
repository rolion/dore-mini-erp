# REV-2026-11-27-gestionar-atencion-odontologica-desde-citas-04: Carrera: finalizar puede cerrar la atención mientras una enmienda crea un borrador vinculado

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-27-gestionar-atencion-odontologica-desde-citas.md (v1)
**Spec reference:** INV-04, AC-09, AC-04
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`finish` comprueba que no haya borradores con `encounter=row` bajo el bloqueo de cita y atención. `EvaluationCommands.amend` (que copia `encounter_id` de la evaluación origen) bloquea la evaluación y al paciente, pero **no** la atención ni la cita, por lo que no se serializa con `finish`.

## Expected behavior
Con INV-04 («nunca finalizar con borrador pendiente»), finalizar y enmendar el odontograma de la misma atención concurrentemente no deberían dejar una atención `finished` con un borrador vinculado.

## Actual behavior
Si la enmienda confirma su borrador entre la comprobación de `finish` y su commit, la atención queda Finalizada con un borrador (`encounter` = esa atención) pendiente. Impacto acotado: el borrador sigue siendo el borrador único del paciente y es editable/descartable desde su ficha; no hay pérdida de datos. No hay prueba de esta carrera (las pruebas concurrentes cubren solo iniciar, crear odontograma y finalizar doble).

## Evidence
- `backend/modules/dentistry/application/encounters.py:80-94` (comprobación de borrador en `finish`).
- `backend/modules/dentistry/application/evaluations.py:84-98` (`amend` sin bloqueo de la atención).
- `backend/modules/dentistry/tests/test_encounter_api.py:319-358` (clases de concurrencia: start, create odontogram, finish).

**Confirmado en la 2.ª pasada:** amend bloquea la atención (lock_encounter) antes de la evaluación y del paciente; orden atención -> paciente consistente con create_odontogram y sin ciclo con finish (cita -> atención). Nota: la prueba de concurrencia solo comprueba coherencia, no discrimina la ausencia del bloqueo; la resolución se confirma por lectura del código.
