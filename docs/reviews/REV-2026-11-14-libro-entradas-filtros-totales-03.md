# REV-2026-11-14-libro-entradas-filtros-totales-03: Huecos de verificación en edge cases y permisos (EDGE-03, EDGE-06, AC-07 no-admin, AC-08 texto libre)

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-14-libro-entradas-filtros-totales.md (v1)
**Spec reference:** EDGE-03, EDGE-06, AC-07, AC-08
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Verificación real ausente o débil para:
- EDGE-03 (`page` fuera de rango -> 404): sin test.
- EDGE-06 (cuenta inactiva después sigue mostrándose en el libro): sin test backend ni spec de componente.
- AC-07 «no admin -> 403»: el test usa un usuario sin empresa (`solo`), no un miembro no administrador de una empresa.
- AC-08 «el listado no contiene texto libre del pago»: solo se comprueba `assertNotIn('reference', row)`; no hay aserción sobre el conjunto exacto de claves.
- Desviación 1 (no se añadieron rutas a `modularity/tests/test_enforcement.py`): razonable, el gate se prueba en `test_accounting_disabled_blocks_the_book`.

## Expected behavior
Cada AC/EDGE tiene una aserción que lo cubra de forma directa (mapeo AC del plan).

## Actual behavior
Comportamiento correcto por lectura del código (DRF devuelve 404 en página inválida; `select_related('account')` no filtra por `is_active`; `CompanyAdminPermission` rechaza no admins), pero sin test que lo fije.

## Evidence
`grep` sobre `backend/modules/accounting/tests/test_entries_api.py` y specs de `features/accounting`: no hay referencias a `page=` fuera de rango, a cuenta desactivada con entradas ni a un usuario de empresa no admin. Suite backend 1569 OK; Karma de las 4 specs de entradas OK.
