# REV-2026-11-04-presentar-aceptar-versionar-proformas-03: company_id sin índice en la tabla de lotes de Odontología

**Status:** Resolved
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-04-presentar-aceptar-versionar-proformas.md (v1)
**Spec reference:** AC-11 (aislamiento por empresa)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El guard `modules.accounts.test_guards.CompanyColumnTests` exige `company_id` obligatorio e indexado en toda tabla raíz de negocio; `DentalProformaDecisionBatchModel` no lo indexaba.

## Expected behavior
`company_id` con índice en `dentistry_proforma_decision_batch`.

## Actual behavior
`AssertionError: Lists differ: ['dentistry.DentalProformaDecisionBatchModel (company_id debe ser obligatorio e indexado)'] != []` (suite completa, 1468 pruebas).

## Evidence
Corregido con `db_index=True` y migración `0003` regenerada (aún no fusionada); `manage.py test modules.accounts modules.dentistry` → `Ran 96 tests ... OK`.
