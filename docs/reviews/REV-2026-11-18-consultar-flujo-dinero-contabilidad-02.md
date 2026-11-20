# REV-2026-11-18-consultar-flujo-dinero-contabilidad-02: Reparto proporcional (INV-04) puede producir un importe externo negativo

**Status:** Resolved (corregido en el commit siguiente; pendiente de reconfirmar en el próximo Quality Gate)
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-18-consultar-flujo-dinero-contabilidad.md (v1)
**Spec reference:** INV-04, INV-03
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`_share` en `domain/ledger_report.py` suma todo el resto de centavos a la primera línea (la mayor) sin acotarlo a su importe. Si hay 3 o más líneas del mismo signo con importes pequeños e iguales, la parte de transferencia asignada a la primera supera su importe y `classify_entry` emite un movimiento externo con importe negativo (`if amount - moved:` es verdadero para negativos).

## Expected behavior
Cada parte (transferencia y externa) está entre 0 y el importe de la línea; Σ se conserva (INV-04 «con centavos exactos»).

## Actual behavior
Asiento con líneas +0,02, +0,02, +0,02 y -0,05 (neto +0,01, T = 0,05): la cuenta A queda con transfer_in 0,03 e inflow -0,01. Totales consolidados siguen cuadrando, pero se muestra una fila de entrada negativa.

## Evidence
```
A transfer_in 0.03
A inflow -0.01
B transfer_in 0.01
B inflow 0.01
C transfer_in 0.01
C inflow 0.01
D transfer_out 0.05
```
Es un caso raro (importes de centavos), pero la regla de resto debería repartir por mayor resto con tope por línea.
