# REV-2026-11-14-pagos-servicios-libro-entradas-02: Faltan pruebas unitarias con fakes y varios casos del plan

**Status:** Resolved
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-14-pagos-servicios-libro-entradas.md (v1)
**Spec reference:** Test Specification; AC-05, AC-09, AC-10, EDGE-02
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El plan pide pruebas de `CollectionService` con un ledger falso (orden, sin cuenta, no disponible, replay sin llamada) y casos sin prueba: `ledger_rejected`, cuenta/mapeo inactivo, Ventas deshabilitado, EDGE-02 y totales del libro.

## Expected behavior
Cada verificación del plan implementada.

## Actual behavior
Solo hay pruebas de integración; el no-llamado del ledger se infiere por conteo de entradas.

## Evidence
`git diff origin/main...HEAD --stat`: sin tests de `application` nuevos.

## Resolución
Añadidas `receivables/tests/test_collection_ledger.py` (fakes: orden, ledger no disponible, fallo, replay) y, en `test_payment_ledger.py`, mapeo/cuenta inactivos, `ledger_rejected`, Ventas deshabilitado, EDGE-02 y totales del libro.
