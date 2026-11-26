# REV-2026-11-26-menu-por-tipo-de-empresa-02: Prueba de AC-03 por tipo es débil

**Status:** Open (aceptado como limitación conocida)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-26-menu-por-tipo-de-empresa.md (v1)
**Spec reference:** AC-03
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`test_rest_of_default_configuration_is_applied_for_every_type` solo cuenta las cuentas contables para cada tipo. Mapeos, categorías de gasto, almacén y ajustes se verifican únicamente con el tipo `odontologia` (`test_company_defaults.py`).

## Expected behavior
Comprobar las secciones de defaults para cada tipo.

## Actual behavior
`compraventa` y `servicios` solo verifican cuentas.

## Evidence
`AccountModel.objects.filter(company_id=company.id).count()` en `backend/modules/accounts/test_company_types.py`. Riesgo bajo: `apply_all` ejecuta todas las secciones sin condicionarlas al perfil; solo `apply_modularity` lo lee.
