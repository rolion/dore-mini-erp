# REV-2026-11-15-modularidad-corte-historicos-contabilidad-01

Status: Open
Severity: Low
Category: IMPLEMENTATION
Related plan: docs/plans/PLAN-2026-11-15-modularidad-corte-historicos-contabilidad.md
Spec reference: AC-03, AC-11, INV-04 (EDGE de empresas existentes)
Plan mode: COMPLETO
Suggested owner: delivery-build

## Description
Una empresa que ya tenía Contabilidad habilitada antes del despliegue y aún no tiene ajustes (ensure perezoso) pierde el registro del hueco si deshabilita antes del primer acceso.

## Expected behavior
Al deshabilitar, el tramo vigente se cierra (o se completa el ensure antes de cerrar) para que la reactivación deje un periodo sin cobertura.

## Actual behavior
OnAccountingDisabled solo llama close_period(): sin tramo abierto no hace nada; al reactivar se abre un tramo nuevo sin hueco previo y el corte se crea en la reactivación.

## Evidence
backend/modules/accounting/application/coverage.py (OnAccountingDisabled.execute); backend/modules/accounting/infrastructure/lifecycle.py (on_disabled). Solo afecta a empresas con módulo habilitado antes del despliegue y sin ningún acceso a settings/libro/coverage_status. Código leído; sin prueba que lo cubra.

## Resolución
Resuelto: `OnAccountingDisabled` completa el corte y el tramo (`EnsureSettings`) antes de cerrar, así una empresa anterior que deshabilita sin haber entrado a Contabilidad conserva su cobertura y la reactivación abre un segundo tramo. Prueba: `test_disabling_a_legacy_company_before_any_access_still_records_its_coverage`.
