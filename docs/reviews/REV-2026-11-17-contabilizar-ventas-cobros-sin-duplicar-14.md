# REV-2026-11-17-contabilizar-ventas-cobros-sin-duplicar-14: Nombre de prueba duplicado y falta la prueba de Pasivo para Anticipos de clientes

**Status:** Resolved (prueba de Pasivo para `CUSTOMER_ADVANCES` y nombre de prueba corregido)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-17-contabilizar-ventas-cobros-sin-duplicar.md (v3)
**Spec reference:** AC-01
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`test_posting_domain.py` tiene un nombre de prueba con texto repetido, y no hay prueba de PUT `CUSTOMER_ADVANCES` con una cuenta que no es Pasivo → 400.

## Expected behavior
Nombre limpio y prueba de la validación de clasificación.

## Actual behavior
Solo se cubre `account_problem` genérico.

## Evidence
`test_posting_domain.py`; `test_posting_config_api.py`. Hallado por el Quality Gate v3 (subagente aislado, 2026-11-17).
