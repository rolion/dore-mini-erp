# REV-2026-11-03-administrar-catalogo-servicios-02: Actualizar expectativa del catálogo de módulos

**Status:** Closed
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-02-administrar-catalogo-servicios.md (v2)
**Spec reference:** AC-06 y contrato del módulo Servicios
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
La prueba de regresión `ListModulesTests.test_defaults_on_first_access` seguía esperando el catálogo anterior sin la entrada `services`.

## Expected behavior
La respuesta de `/api/modules/` incluye `services` después de `catalog`, deshabilitado por defecto.

## Actual behavior
La ejecución con PostgreSQL falló en 1 de 109 pruebas:
```text
FAIL: test_defaults_on_first_access (modules.modularity.tests.test_api.ListModulesTests.test_defaults_on_first_access)
First differing element 2:
'services'
'customers'
Ran 109 tests in 3.921s
FAILED (failures=1)
```

## Evidence
`backend/modules/modularity/tests/test_api.py` esperaba `['access', 'catalog', 'customers', ...]`.

## Corrección delivery-build
Se añadió `services` a la expectativa de orden; el conjunto de módulos habilitados por defecto se mantiene. Repetición contra PostgreSQL local con base de pruebas exclusiva:
```text
Ran 109 tests in 3.956s
OK
System check identified no issues (0 silenced).
```
