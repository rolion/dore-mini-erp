# REV-2026-10-27-habilitar-modulos-por-empresa-02: EDGE-03 se prueba de forma secuencial, no concurrente

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-27-habilitar-modulos-por-empresa.md (v1)
**Spec reference:** EDGE-03, Test Specification (API: «EDGE-03 doble sembrado»)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-engineer

## Description
`test_repeated_reads_do_not_duplicate_defaults` hace dos `GET` seguidos y comprueba 4 filas. Eso valida idempotencia, pero no la condición de carrera de dos primeras lecturas simultáneas (el riesgo que mitigan la unicidad y `ignore_conflicts`). Tampoco hay un test que fuerce el camino en que `CompanySettingsModel` ya existe pero faltan filas.

## Expected behavior
EDGE-03: «Dos primeras lecturas simultáneas de la misma empresa → sin duplicados ni error 500».

## Actual behavior
El código es razonable (`get_or_create` dentro de `transaction.atomic()` + `bulk_create(ignore_conflicts=True)` + restricción única) y la restricción impide duplicados, pero la concurrencia no está ejercitada por ningún test.

## Evidence
`backend/modules/modularity/tests/test_api.py` (`test_repeated_reads_do_not_duplicate_defaults`); `backend/modules/modularity/infrastructure/django/repositories.py:enabled_keys`. `python manage.py test modules.modularity` → 22 tests OK. Sugerencia: test de repositorio que simule el conflicto (insertar la fila de settings o un módulo por defecto antes del sembrado) o `TransactionTestCase` con hilos.
