# REV-2026-11-25-numeracion-correlativa-pedidos-venta-01: La prueba de carrera confirmar vs. cerrar (AC-08) no detecta la ausencia del bloqueo

**Status:** Resolved
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-25-numeracion-correlativa-pedidos-venta.md (v1)
**Spec reference:** AC-08; Test Specification > Concurrency tests (3.er punto); Acceptance criteria mapping (AC-08)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`ConcurrentNumberingTests.test_confirming_against_a_close_never_numbers_inside_a_closed_period` (`backend/modules/sales/tests/test_order_numbering_concurrency.py`) lanza 3 confirmaciones, una primera confirmación y un cierre del período en hilos simultáneos, sin ningún punto de sincronización determinista sobre el bloqueo del período.

## Expected behavior
El plan exige: «si el cierre gana, la confirmación recibe `fiscal_period_closed`; si la confirmación gana, queda numerada y luego se cierra; nunca numerada en período ya cerrado». La prueba debe fallar si `lock_open_period` deja de serializar confirmar y cerrar (como sí hace `accounting/tests/test_fiscal_period_concurrency.py::CloseVsPostingTests`, que sostiene el bloqueo con un `Event` y una espera).

## Actual behavior
Las aserciones son: (a) los únicos errores permitidos son `fiscal_period_closed`; (b) los números asignados son `1..k` sin huecos; (c) el período termina CLOSED; (d) una confirmación posterior al cierre falla. Ninguna comprueba que alguna confirmación haya sido numerada antes del cierre ni que ninguna se numerara después de él. Si se quitara el bloqueo de `lock_open_period` (conservando el `select_for_update` del contador), todas las confirmaciones concurrentes seguirían numerándose 1..k, el cierre terminaría y (a)-(d) se cumplirían: la prueba pasa sin el comportamiento que dice verificar. Si el cierre gana siempre, `numbered == []` y también pasa (caso vacío). La nota de mutación del TASK solo menciona las tres pruebas de carrera de numeración, no esta.
Es una inspección de código; no se ejecutó la mutación porque el revisor no puede modificar el repo.

## Evidence
- `test_order_numbering_concurrency.py` (líneas del test AC-08): `started` se activa al inicio de `first_confirm`, antes de tomar ningún bloqueo; `unexpected` solo filtra excepciones; `self.assertEqual(numbered, list(range(1, len(numbered) + 1)))` es verdadero para `[]`.
- Referencia del patrón robusto: `backend/modules/accounting/tests/test_fiscal_period_concurrency.py` (`post(locked, hold=0.5)` + `close(locked)` con `assertEqual(self.events, ['posted', 'closed'])`).
- Sugerencia: una confirmación que retiene el período (evento + pausa tras `next_number`) y un cierre que arranca después; afirmar que la confirmación queda numerada y el cierre ocurre después; y el caso inverso (cierre confirmado antes → `fiscal_period_closed`, sin número ni avance del contador).

## Resolución
Resuelto: la prueba AC-08 se reescribió con sincronización determinista (`test_a_close_waits_for_the_confirmation_in_flight`: la confirmación retiene el bloqueo del período y el cierre debe esperarla; y `test_after_a_committed_close_confirming_is_rejected_without_numbering`). Comprobado por mutación: sustituyendo `lock_open_period` por `period_for` la prueba falla (`['closed', 'numbered'] != ['numbered', 'closed']`).
