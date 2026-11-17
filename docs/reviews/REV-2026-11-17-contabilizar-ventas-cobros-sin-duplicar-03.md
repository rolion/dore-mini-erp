# REV-2026-11-17-contabilizar-ventas-cobros-sin-duplicar-03: Faltan pruebas unitarias con puertos falsos

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-17-contabilizar-ventas-cobros-sin-duplicar.md (v1)
**Spec reference:** PLAN › Unit tests
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El plan prevé pruebas de los comandos con puertos falsos (`sales/tests/fakes.py`); no se añadieron.

## Expected behavior
Pruebas de orden, bloqueos, cancelación, replay y total 0 sin BD.

## Actual behavior
La cobertura es por integración vía API; `fakes.py` sin cambios.

## Evidence
`backend/modules/sales/tests/fakes.py`. Hallado por el Quality Gate (subagente aislado, 2026-11-17); suite backend 1986 OK y frontend 1574 OK.
