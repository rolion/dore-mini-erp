# REV-2026-11-28-reportes-proformas-odontologia-01: Casos de borde y pruebas unitarias del plan sin cubrir

**Status:** Closed (pruebas agregadas; ver commit de cierre)
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-28-reportes-proformas-odontologia.md (v1)
**Spec reference:** Edge cases / Error cases; Test Specification > Unit tests e Integration tests; AC-06, AC-07, AC-09
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El PLAN declara varios casos de borde y pruebas que no existen en el diff.

## Expected behavior
- Edge case «pago mayor al aceptado (rectificación) → se trata como pagada»: prueba que el pago excedente aparece en «Pagadas» con Monto = total cobrado y no en «Por cobrar».
- Edge case «proforma sin doctor o con profesional borrado → «—»»: prueba de la columna Doctor en la exportación (xlsx/pdf) sin doctor y con profesional inexistente (API devuelve `doctor` con nombre vacío).
- Unit tests: «`shared/report_export`: columnas declaradas, formato de dinero, neutralización de fórmulas» (`shared/tests/test_report_export`), incluida regresión de `build_xlsx`/`build_pdf` tras delegar en `build_table_*` (AC-12).
- AC-09 «mismos permisos que la lista de proformas»: prueba de un usuario sin acceso clínico (`CompanyClinicalPermission`) recibiendo 403 en lista y exportación.

## Actual behavior
`test_proforma_reports_api.py` solo contiene 8 pruebas (lista/pagadas, fechas, totales, exportación con `=`, límite, aislamiento, módulos, versiones). No hay prueba de sobrepago, de profesional borrado, de «—» en exportación ni de permiso clínico; no existe ningún test de `shared/report_export` (`grep -rln report_export` en pruebas: ninguno); la regresión de ventas/compras depende solo de pruebas indirectas.

## Evidence
```
$ grep -n "def test_" backend/modules/dentistry/tests/test_proforma_reports_api.py
69 test_receivable_and_paid_lists_split_by_collection / 93 test_date_filter_is_inclusive_and_validated /
105 test_totals_cover_every_page / 114 test_exports_have_same_rows_and_neutralize_formulas / 132 test_export_limit /
139 test_company_isolation / 156 test_requires_both_modules / 164 test_superseded_versions_are_not_listed_twice
$ grep -rln "report_export" --include=*.py backend (excluyendo .venv)
modules/dentistry/api/proforma_report_views.py, modules/purchases/api/purchase_report_views.py, modules/sales/api/views.py   (ninguna prueba)
```
El comportamiento actual del código parece correcto para esos casos (`collected >= accepted` -> pagada; nombre vacío -> `null`/«—»); el riesgo es de regresión sin red de pruebas.
