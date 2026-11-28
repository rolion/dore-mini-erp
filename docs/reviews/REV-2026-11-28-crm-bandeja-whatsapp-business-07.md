# REV-2026-11-28-crm-bandeja-whatsapp-business-07: Dos pruebas de fronteras de módulos fallan: `crm` → `messaging` no figura como dependencia permitida

**Status:** Resolved (pendiente de re-verificación por el Quality Gate)
**Severity:** High
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-28-crm-bandeja-whatsapp-business.md (v1)
**Spec reference:** ADR-crm-bandeja-whatsapp-business-bandeja-en-crm-sobre-fachada-de-messaging; PLAN «Regression tests» y paso 9; docs/architecture/ddd.md (reglas de fronteras)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El ADR decide que `crm` consume `messaging` solo por `modules.messaging.services`. La prueba de fronteras (`backend/modules/sales/tests/test_boundaries.py`) mantiene una lista blanca `ALLOWED_DEPENDENCIES` en la que `crm` solo puede depender de `{'customers', 'sales', 'inventory'}` y `messaging` declara `set()` con el comentario «otros la consumirán por su fachada». La tarea añadió `crm/infrastructure/adapters.py` y `crm/infrastructure/inbox_subscriber.py` que importan `modules.messaging` pero no actualizó la lista blanca (ni lo menciona como desviación).

## Expected behavior
La suite completa del backend pasa; si `crm → messaging` (por `services.py`) es una dependencia intencionada, queda declarada en `ALLOWED_DEPENDENCIES` (y la excepción de que solo se importe `services`, no infraestructura, sigue verificada).

## Actual behavior
`python manage.py test` falla en 2 pruebas de la suite de fronteras. El autor solo ejecutó `modules.crm` y `modules.messaging` (231 OK), por eso no lo vio.

## Evidence
`manage.py test --noinput` (DJANGO_SETTINGS_MODULE=config.settings.test) → `Ran 2653 tests in 516.767s — FAILED (failures=2)`:
- `FAIL: test_consumers_reach_other_modules_only_from_their_adapters (modules.sales.tests.test_boundaries.ModuleBoundaryTests)` → `['modules\crm\infrastructure\inbox_subscriber.py importa modules.messaging'] != []`
- `FAIL: test_modules_only_reach_allowed_modules_and_only_through_services (...)` → `['modules\crm\infrastructure\adapters.py importa modules.messaging', 'modules\crm\infrastructure\inbox_subscriber.py importa modules.messaging'] != []`

`test_boundaries.py:31` `'crm': {'customers', 'sales', 'inventory'}`; `test_boundaries.py:33` `'messaging': set()`. El archivo no está en el diff `origin/crm...HEAD`.


## Resolution
`test_boundaries.py` declara crm → messaging; la suscripción pasa por `crm/infrastructure/adapters.py`.
