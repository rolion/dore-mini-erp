# REV-2026-11-15-cuentas-dinero-clasificaciones-01: AC-04 sin el test de migración que el plan prometía

**Status:** Open
**Severity:** Low
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-11-15-cuentas-dinero-clasificaciones.md (v1)
**Spec reference:** AC-04
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start (alinear plan) / delivery-build (opcional)

## Description
El mapeo de AC-04 del plan dice «regresión `test_unified_journey` + test de migración sobre entradas». No existe test de migración; la desviación está documentada en `## Implementación` del TASK.

## Expected behavior
O bien un test que cree entradas antes de `0004` y verifique referencias/montos después, o bien el plan ajustado para no prometerlo.

## Actual behavior
AC-04 se cubre solo por la regresión de la suite completa (1663 OK). La migración `0004` es aditiva (`AddField` anulable + `CreateModel`; no toca `EntryModel`), por lo que el riesgo real es mínimo y la cobertura se considera suficiente.

## Evidence
`git diff origin/main...HEAD -- backend/modules/accounting/migrations/0004_account_kind_classification.py`: solo `migrations.AddField(... kind ... null=True)` y `migrations.CreateModel(ClassificationModel)`. `manage.py makemigrations --check --dry-run` -> "No changes detected". `manage.py test` -> "Ran 1663 tests in 242.104s OK".
