# REV-2026-10-27-configuracion-por-modulo-y-empresa-02: EDGE-03 (concurrencia) sin test pese a estar en la Test Specification

**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-27-configuracion-por-modulo-y-empresa.md (v1)
**Spec reference:** EDGE-03, INV-03
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El plan (Integration tests) exige un test de concurrencia para guardados simultaneos del mismo ajuste. El bloqueo existe (`select_for_update` sobre modularity_company_settings en `lock_values`), pero no hay ningun test concurrente; el TASK lo declara como desviacion (4).

## Expected behavior
Dos guardados simultaneos generan cada uno su registro con el valor anterior real; verificado por test.

## Actual behavior
Solo hay tests secuenciales; el comportamiento bajo concurrencia real no esta verificado. Lectura del codigo: lock_values bloquea la fila de empresa y relee los valores dentro del atomic de la vista, por lo que el diseno es correcto.

## Evidence
grep de def test en modules/modularity/tests/test_settings_api.py: ningun test de hilos/concurrencia. Sugerencia: TransactionTestCase con dos hilos (o verificar que la consulta emitida contiene FOR UPDATE con CaptureQueriesContext) para dejar evidencia.
