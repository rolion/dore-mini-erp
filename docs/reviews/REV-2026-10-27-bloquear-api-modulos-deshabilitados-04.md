# REV-2026-10-27-bloquear-api-modulos-deshabilitados-04: Cobertura débil de AC-05 y de métodos OPTIONS/HEAD

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-27-bloquear-api-modulos-deshabilitados.md (v1)
**Spec reference:** AC-05, AC-01 (todos los métodos)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-engineer

## Description
`test_authentication_and_company_are_checked_before_the_module` acepta `(401, 403)` para el caso sin sesión (debería ser 401 con TokenAuthentication) y no cubre empresa inactiva ni rol distinto de admin antes del módulo. La tabla de rutas recorre GET/POST/PATCH/DELETE pero no OPTIONS/HEAD. No encontré un bypass: DRF evalúa los permisos en `initial()` antes de resolver el manejador, también para OPTIONS y HEAD.

## Expected behavior
Pruebas que fijen el 401 exacto, la empresa inactiva y OPTIONS/HEAD sobre un módulo deshabilitado.

## Actual behavior
La regresión de esos casos no quedaría detectada por la suite.

## Evidence
`backend/modules/modularity/tests/test_enforcement.py:116-130` (`assertIn(response.status_code, (401, 403))`) y la tabla `ROUTES` (líneas 14-45).
