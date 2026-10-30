# REV-2026-10-30-habilitar-produccion-y-costeo-01: Falta la prueba 403 `module_disabled` para `production`/`costing` prometida para AC-03

**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-30-habilitar-produccion-y-costeo.md (v1)
**Spec reference:** AC-03; tabla «Acceptance criteria mapping» (AC-03: «API: vista de prueba con `required_modules=('production',)` 403/200»); Test Specification > Integration tests
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El plan exige, para AC-03 («la API de módulos de Producción/Costeo responde 403 `module_disabled` si el módulo está deshabilitado»), una prueba de integración con una vista de prueba que declare `required_modules=('production',)` y verifique 403 deshabilitado / 200 habilitado.

## Expected behavior
Existe una prueba (p. ej. en `test_enforcement.py` o `test_production_costing_api.py`) que demuestre que `CompanyModulePermission` responde 403 `{code: 'module_disabled', module: 'production'|'costing'}` con el módulo deshabilitado y permite el acceso con el módulo habilitado. Si se omite, la desviación debe constar en `## Implementación` del TASK.

## Actual behavior
Ninguna prueba del diff ejercita `module_disabled` con `production` ni `costing` (`grep module_disabled` solo aparece en `test_enforcement.py` para los módulos de negocio previos y en `purchases`). La sección «Desviaciones» del TASK documenta el archivo de pruebas nuevo, la propagación del gancho y la ausencia de `test_guards` nuevo, pero no esta omisión. AC-03 queda cubierto solo por el spec de sidebar (menú) y por `capability_available`/`missing_capabilities`; la parte «API respeta módulos» no tiene prueba específica (el mecanismo es genérico y `test_guards` valida las claves contra el catálogo, pero no hay evidencia directa).

## Evidence
- `git diff origin/main...HEAD --stat`: no hay cambios en `test_enforcement.py` ni `test_guards.py`.
- `grep -rn module_disabled backend`: `config/permissions.py`, `modularity/tests/test_enforcement.py:68`, `purchases/tests/*`; ninguna referencia a `production`/`costing`.
- TASK `## Implementación > Desviaciones`: no menciona esta prueba.
