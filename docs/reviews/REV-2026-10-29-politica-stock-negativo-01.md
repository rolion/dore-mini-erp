# REV-2026-10-29-politica-stock-negativo-01: AC-04/INV-03 sin prueba nueva ni verificación: la atomicidad de la política no está demostrada

**Status:** Partially addressed (falta correr concurrencia en PostgreSQL)
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-29-politica-stock-negativo.md (v1)
**Spec reference:** AC-04, INV-03, EDGE-05; Test Specification > Concurrency tests; Implementation steps #4
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El plan exige una prueba de concurrencia en PostgreSQL (paso 4) y el TASK declara como desviación que no se añadió ninguna porque `test_simultaneous_exits_cannot_overdraw_the_balance` ya cubre AC-04. Ese test preexistente no ejercita la lectura de la política dentro de `locked()` y ninguna prueba comprueba que `allow_negative_stock()` se invoque con el bloqueo del almacén ya tomado (INV-03). Además no es ejecutable aquí: sin PostgreSQL no se pudo verificar.

## Expected behavior
Una prueba (TransactionTestCase en PostgreSQL, o un unit con puerto de política falso que verifique que se consulta dentro de `locked`) que demuestre INV-03 y AC-04 con la política en juego (EDGE-05).

## Actual behavior
La lectura dentro del bloqueo es correcta por inspección de código (`movement_use_cases.py`: `_check_balance` y la rama de `ReverseMovement` se ejecutan dentro del `with ...locked(...)`), pero no hay prueba que lo proteja de una regresión, y la prueba de concurrencia existente no pudo ejecutarse.

## Evidence
SQLite (sin bloqueo de filas): `ConcurrencyTests.test_simultaneous_exits_cannot_overdraw_the_balance` FALLA tanto en la rama como en origin/main (mismo conjunto de fallos de concurrencia en ambas) => no verificable sin PostgreSQL, no es PASS. Grep: ningún test referencia el orden política/bloqueo.
