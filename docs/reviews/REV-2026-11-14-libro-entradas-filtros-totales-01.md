# REV-2026-11-14-libro-entradas-filtros-totales-01: account_id inexistente o ajeno en el filtro devuelve 200 vacío en vez de 400

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-14-libro-entradas-filtros-totales.md (v1)
**Spec reference:** EDGE-02, AC-07
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
EDGE-02 dice que `account_id`/`method`/`origin` desconocidos responden 400 «(no listan nada ajeno)». `EntryFiltersSerializer.account_id` solo valida el formato UUID; un UUID bien formado que no existe en la empresa (o que es de otra empresa) produce 200 con `count: 0` y totales vacíos.

## Expected behavior
Una cuenta desconocida para la empresa se rechaza con 400 (o la Specification se aclara para aceptar el 200 vacío).

## Actual behavior
`GET /api/accounting/entries/?account_id=<uuid de otra empresa>` -> 200, `count=0`. No hay fuga de datos (el aislamiento se cumple), por eso es Low. El test `test_invalid_filters_are_rejected` solo prueba un UUID malformado (`'no-uuid'`) y `test_each_company_only_sees_its_own_entries` afirma explícitamente `count == 0` con cuenta ajena.

## Evidence
`backend/modules/accounting/api/serializers.py`: `account_id = serializers.UUIDField(required=False)` sin comprobación de pertenencia. `backend/modules/accounting/tests/test_entries_api.py::test_each_company_only_sees_its_own_entries` (`...get(ENTRIES, {'account_id': str(self.caja.id)}).data['count'], 0`). La suite pasa (1569 OK), es una discrepancia de interpretación de la Specification, no un fallo.

## Resolution
Cuenta desconocida o ajena en `account_id` → 400 `{account_id: [...]}` (EntryListView valida pertenencia con `DjangoAccountRepository(company_id)`); `test_each_company_only_sees_its_own_entries` ahora exige el 400.
