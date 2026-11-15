# REV-2026-11-15-conciliar-regularizar-pagos-historicos-01: El informe no reporta el filtro de periodo ni la cobertura del mapeo (AC-08) ni declara el módulo deshabilitado (EDGE-05)

**Status:** Resolved
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-14-conciliar-regularizar-pagos-historicos.md (v2)
**Spec reference:** AC-08, EDGE-05, API-01
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
AC-08 exige que el informe «reporte el filtro de periodo y la cobertura del mapeo»; EDGE-05 dice que, con `accounting` deshabilitado, el comando funciona igual y «lo declara el informe». El resumen compartido (`accounting/application/regularization_summary.py::build_summary`) devuelve solo `mode`, `total_payments`, `groups`, `absent_fields`, `excluded_voided*` y `details`; el comando (`management/commands/regularize_ledger.py::render`) no imprime periodo ni cobertura ni el estado del módulo. Tampoco la pantalla.

## Expected behavior
El resumen (JSON/texto/UI) incluye el periodo aplicado (`date_from`/`date_to` o «sin filtro»), la cobertura del mapeo (métodos con reglas y sus rangos, y/o cuántos pagos quedaron sin regla) y, en el comando, la advertencia de que `accounting` está deshabilitado para la empresa cuando lo esté.

## Actual behavior
Nada de eso aparece. La prueba `test_report_groups_by_origin_account_currency_and_period_filter` solo verifica que el filtro reduce los grupos, no que el informe lo reporte; ninguna prueba cubre EDGE-05.

## Evidence
- `grep -rniE "period|coverage|cobertura|module_gate|enabled" backend/modules/accounting/application/regularization_summary.py backend/modules/accounting/management/commands/regularize_ledger.py` → solo coincide la palabra `period` en el nombre de la prueba; en el código de producción no hay coincidencias (salvo `--from/--to` como argumentos).
- Claves devueltas por `build_summary`: `mode, total_payments, groups, absent_fields, excluded_voided, excluded_voided_note, details`.
- `docs/tasks/TASK-...md` `## Implementación` no declara esta omisión como desviación.

## Resolución
El resumen (API, comando y pantalla) ahora trae `period`, `mapping_coverage` (reglas aplicadas por método con cuenta y rango), `unmapped_methods` y `accounting_enabled`. El comando imprime «Periodo: …», «Regla: …», «Métodos sin regla …» y, con Contabilidad deshabilitada, «AVISO: Contabilidad está deshabilitada…» (EDGE-05); la pantalla lo muestra bajo el titular. Cambio aditivo del contrato. Pruebas: `test_report_states_the_period_and_the_mapping_coverage`, `test_report_declares_when_accounting_is_disabled_but_still_works`, aserciones en la prueba de la API y spec del componente.
