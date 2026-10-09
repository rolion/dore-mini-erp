# REV-2026-10-09-gastos-reporting-mvp-02: UI-03 prohíbe palabras que el DDR y API-04 exigen ("utilidad", "costo")

**Status:** Open
**Severity:** Low
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-10-09-gastos-reporting-mvp.md (v1)
**Spec reference:** UI-03, AC-25, API-04
**Plan mode:** COMPLETO
**Suggested owner:** delivery-plan

## Description
La Specification se contradice: UI-03 dice "rótulo literal 'Ganancia estimada'; sin las palabras 'costo', 'margen' ni 'utilidad'", pero (a) el DDR del dashboard fija la nota "Ventas − gastos registrados. Es una estimación, no la utilidad contable." y (b) API-04 fija el criterio "…La ganancia estimada no incluye costo de producción.", que AC-25/26 obligan a mostrar.

## Expected behavior
Una Specification coherente: o UI-03 se acota a "no insinuar costo real/margen" (la intención de REQ-REP-005), o se cambian los textos fijos.

## Actual behavior
La implementación sigue fielmente el DDR y API-04 (`dashboard.component.ts:13` `ESTIMATE_NOTE`; `reporting/application/criteria.py`), por lo que incumple la letra de UI-03. Ambas frases niegan explícitamente costo/utilidad, así que no insinúan lo que REQ-REP-005 prohíbe.

## Evidence
```
$ grep -rniE "costo|margen|utilidad" frontend/panel_admin/src/app/features/reporting backend/modules/reporting (sin tests)
dashboard.component.ts:13: ... Es una estimación, no la utilidad contable.
criteria.py:5: ... La ganancia estimada no incluye costo de producción.
```
Acción: `delivery-plan` reformula UI-03 (sin cambio de código). No requiere cambiar comportamiento de negocio.
