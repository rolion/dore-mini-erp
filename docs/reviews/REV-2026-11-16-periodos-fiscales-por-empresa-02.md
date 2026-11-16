# REV-2026-11-16-periodos-fiscales-por-empresa-02: Falta prueba de permisos no admin → 403 en fiscal-periods

**Status:** Resolved (corregido en la rama; ver commit)
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-16-periodos-fiscales-por-empresa.md (v1)
**Spec reference:** Authorization
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El PLAN pide «no admin 403, sin empresa 403»; solo se prueba 401 y sin empresa 403. El permiso funciona por herencia del default pero no está verificado para fiscal-periods (incluidos close/reopen).

## Expected behavior
Añadir la prueba con un usuario de otro rol siguiendo test_entries_api.py.

## Actual behavior
Ver descripción.

## Evidence
Quality Gate (subagente aislado), backend/modules/accounting/tests/test_fiscal_periods_api.py:99-107. Backend 1678 OK; frontend 1430 OK (2 de 3 corridas, ver nota del flake preexistente `screens-i18n.spec.ts:58-65`, ajeno al diff).
