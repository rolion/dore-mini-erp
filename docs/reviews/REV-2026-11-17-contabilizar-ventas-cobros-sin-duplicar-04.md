# REV-2026-11-17-contabilizar-ventas-cobros-sin-duplicar-04: Casos de la Specification sin prueba explícita

**Status:** Resolved (pruebas de total 0, replay con configuración cambiada y período cerrado al cobrar)
**Severity:** Low
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-11-17-contabilizar-ventas-cobros-sin-duplicar.md (v1)
**Spec reference:** EDGE-01, EDGE-03, EDGE-05, AC-06, AC-09, AC-11
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Sin prueba: total 0 sin asiento, cobro anterior al reconocimiento, replay con configuración cambiada, período cerrado al cobrar, hueco/antes del corte con módulo habilitado.

## Expected behavior
Cada AC/EDGE con verificación asignada.

## Actual behavior
Implementados (p. ej. `order.total > 0` en `commands.py`) pero no verificados.

## Evidence
`test_sales_posting.py`. Hallado por el Quality Gate (subagente aislado, 2026-11-17); suite backend 1986 OK y frontend 1574 OK.
