# REV-2026-11-26-registrar-diagnostico-odontograma-inicial-07: La suite completa falla: guard de company_id y prueba de fronteras entre módulos no contemplan los cambios

**Status:** Closed
**Severity:** High
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-26-registrar-diagnostico-odontograma-inicial.md (v1)
**Spec reference:** Regression tests del plan («Suites existentes»); CLAUDE.md (aislamiento por empresa; los módulos no se importan infraestructura entre sí); Architecture considerations del plan (dependencia dentistry → personnel por fachada)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Dos pruebas de guardia existentes, fuera de `modules.dentistry`, fallan con el diff de la rama (la regresión parcial `personnel/customers/modularity/config/dentistry` pasa; solo la suite completa lo detecta):

1. `modules/accounts/test_guards.py:36` (`CompanyColumnTests`): los modelos hijos `dentistry.EvaluationFindingModel` y `dentistry.EvaluationGeneralFindingModel` no tienen `company_id` y no figuran en `CHILD_MODELS` (la guardia exige columna `company_id` en toda tabla de negocio o registro explícito como hijo).
2. `modules/sales/tests/test_boundaries.py:23,87`: el mapa de dependencias permitidas de `dentistry` es `{'customers', 'service_catalog'}`; `infrastructure/adapters.py` importa ahora `modules.personnel.services`. La dependencia está documentada en `docs/architecture/ddd.md` (nota PB-ODO-002) y en el ADR, pero no se actualizó el mapa de la prueba.

## Expected behavior
`python manage.py test` completo en verde: los hijos de evaluación registrados como modelos hijo (o con `company_id`), y la dependencia `dentistry → personnel` autorizada en el mapa de la prueba de fronteras (cambio acotado y declarado).

## Actual behavior
```
FAIL: test_every_root_business_table_has_company_id (modules.accounts.test_guards.CompanyColumnTests...)
AssertionError: Lists differ: ['dentistry.EvaluationFindingModel', 'dentistry.EvaluationGeneralFindingModel'] != []
FAIL: test_modules_only_reach_allowed_modules_and_only_through_services (modules.sales.tests.test_boundaries.ModuleBoundaryTests...)
AssertionError: ... 'modules\\dentistry\\infrastructure\\adapters.py importa modules.personnel.services'
Ran 2592 tests in 421.562s
FAILED (failures=2)
```

## Evidence
Salida literal de `python manage.py test --noinput` completa (DJANGO_SETTINGS_MODULE=config.settings.test, TEST_DATABASE_NAME=test_dore_odo002_full), arriba. No se comprobó contra `main` por separado, pero los dos fallos nombran exclusivamente código añadido por esta rama.


## Verificación Quality Gate #2
Cerrado. `python manage.py test --noinput`: Ran 2597 tests in 457.618s, OK (accounts.test_guards y sales.tests.test_boundaries incluidos).
