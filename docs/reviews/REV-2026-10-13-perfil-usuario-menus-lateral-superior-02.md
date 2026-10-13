# REV-2026-10-13-perfil-usuario-menus-lateral-superior-02: Falta el test de clic en Logout previsto en la Test Specification

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-13-perfil-usuario-menus-lateral-superior.md (v1)
**Spec reference:** AC-06 ("Logout sigue cerrando la sesión"); Test Specification (AC-04/05/06: "clic en Logout llama `logout()`")
**Plan mode:** COMPACTO
**Suggested owner:** delivery-engineer

## Description
`header.component.spec.ts` verifica que el menú contiene solo `['Logout']`, nombre y empresa, pero ninguna prueba hace clic en `.logout-item` ni comprueba que se llame a `AuthService.logout()`. El `AuthService` simulado del spec ni siquiera define `logout`.

## Expected behavior
Test Specification del plan: "clic en Logout llama `logout()`" (AC-06).

## Actual behavior
La mitad de AC-06 ("Logout sigue cerrando la sesión") queda sin verificación automatizada tras reescribir la plantilla del menú.

## Evidence
`grep -n "logout" frontend/panel_admin/src/app/layout/header/header.component.spec.ts` solo encuentra el texto `'Logout'` en la aserción de enlaces (línea ~91) y el selector indirecto; no hay `spyOn`/`click` sobre `.logout-item`.
