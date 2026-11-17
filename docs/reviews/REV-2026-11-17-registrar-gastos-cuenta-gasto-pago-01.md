# REV-2026-11-17-registrar-gastos-cuenta-gasto-pago-01: Falta la prueba de concurrencia real (TransactionTestCase) exigida por el Test Specification

**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-17-registrar-gastos-cuenta-gasto-pago.md (v1)
**Spec reference:** AC-04, INV-04; Test Specification (Integration tests) y tabla AC->verificacion
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El plan exige para AC-04 una prueba con `TransactionTestCase` de dos peticiones concurrentes con la misma `idempotency_key`. La implementacion solo simula la carrera con un fake (`test_losing_the_race_returns_the_winner`) y lo declara como desviacion en el TASK.

## Expected behavior
Existe una prueba multihilo contra PostgreSQL que demuestre un solo gasto y un solo asiento (indice unico parcial + punto de guardado del repositorio).

## Actual behavior
No hay prueba multihilo en el repositorio. El revisor ejecuto una sonda externa (dos hilos, `CreateExpense` real, `AccountingPosting` real, barrera): resultado `[(id, False), (id, True)]`, 1 gasto y 1 asiento, es decir el comportamiento es correcto, pero no queda cubierto por la suite.

## Evidence
- `backend/modules/expenses/tests/test_posting_application.py:106` (carrera simulada).
- Sonda del revisor (fuera del repo): `RACE [('acfc3e3b-...', False), ('acfc3e3b-...', True)] []`, `RACE-COUNT 1`, `RACE-ENTRIES 1`.
- TASK, seccion Implementacion: "no hay TransactionTestCase multihilo".
