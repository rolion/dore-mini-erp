# REV-2026-11-18-consultar-flujo-dinero-contabilidad-01: Aserciones de conteo incorrectas en pruebas de integración (test_cash_flow_detail.py)

**Status:** Resolved (corregido en el commit siguiente; pendiente de reconfirmar en el próximo Quality Gate)
**Severity:** High
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-18-consultar-flujo-dinero-contabilidad.md (v1)
**Spec reference:** AC-02, AC-06
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
En `backend/modules/accounting/tests/test_cash_flow_detail.py` dos aserciones de `count` no coinciden con los asientos que crea cada prueba. Las pruebas con BD no se pudieron ejecutar (sin PostgreSQL), pero el conteo se reprodujo con el dominio real (`build_cash_flow_movements`).

## Expected behavior
`test_account_balances_match_the_ledger_and_movements_back_the_totals`: en el rango 2026-05-01..31 hay 300 (entrada), 50 (salida) y una transferencia de 40 (2 filas: recibida y enviada) = 4 filas (el asiento del 20-abr queda fuera del rango). `test_filters_by_account_type_and_range`: 300, 80, 50 y transferencia (2 filas) = 5 filas.

## Actual behavior
Las pruebas afirman `result['count'] == 5` (debe ser 4) y `self.moves(page_size=2)['count'] == 6` (debe ser 5). Fallarán al correr con PostgreSQL.

## Evidence
Simulación con el dominio: entradas [cash +300, bank +80, cash -50, transfer bank+40/cash-40] -> `len(build_cash_flow_movements(...)) == 5`; sin el asiento de 80 -> 4. Las aserciones dicen 6 y 5 respectivamente.
