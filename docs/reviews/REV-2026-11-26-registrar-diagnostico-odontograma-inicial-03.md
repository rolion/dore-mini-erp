# REV-2026-11-26-registrar-diagnostico-odontograma-inicial-03: Orden de bloqueos inconsistente entre amend y confirm/update/discard (riesgo de deadlock)

**Status:** Closed
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-26-registrar-diagnostico-odontograma-inicial.md (v1)
**Spec reference:** Edge case «Dos confirmaciones simultáneas → la segunda 409 (bloqueo de fila)»; Risks «Concurrencia en sequence y borrador único (bloqueo de fila del paciente + restricción)»
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
En `backend/modules/dentistry/application/evaluations.py`: `update` (l.46-49), `discard` (l.59-61) y `confirm` (l.66-69) bloquean primero la fila de la evaluación y luego la del paciente; `amend` (l.75-77) bloquea primero al paciente y luego la evaluación. `amend` lee la evaluación sin bloqueo (l.75), por lo que puede ver una evaluación aún en borrador mientras otra transacción la está confirmando.

## Expected behavior
Un único orden de adquisición de bloqueos (p. ej. siempre paciente y después evaluación) para que operaciones simultáneas sobre la misma evaluación se serialicen y la segunda reciba 409/400, nunca un error de servidor.

## Actual behavior
`confirm(D)` sostiene la fila de D y espera la del paciente mientras `amend(D)` sostiene al paciente y espera D: PostgreSQL detecta el interbloqueo y aborta una de las dos con error 500 (`deadlock detected`). Ventana muy estrecha (dos pestañas/usuarios actuando sobre la misma evaluación a la vez), sin corrupción de datos (las restricciones únicas `dentistry_evaluation_sequence_unique` y `dentistry_evaluation_one_draft` siguen protegiendo). No hay pruebas de concurrencia (el plan las menciona como borde).

## Evidence
Revisión de código con las líneas citadas; no reproducido (requiere transacciones concurrentes reales).


## Verificación Quality Gate #2
Cerrado. `_locked_row` fija un único orden (paciente y luego evaluación) en update/discard/confirm/amend. `ConcurrentEvaluationTests.test_two_simultaneous_confirms_leave_one_confirmation` (TransactionTestCase, 2 hilos) da [200, 409] y una sola confirmación; suite completa OK.
