# REV-2026-11-28-crm-bandeja-whatsapp-business-05: Huecos de cobertura en aislamiento entre empresas y paginación

**Status:** Resolved (pendiente de re-verificación por el Quality Gate)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-28-crm-bandeja-whatsapp-business.md (v1)
**Spec reference:** PLAN Integration tests (listado/paginado; aislamiento en todos los endpoints); AC-01; AC-10
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El código filtra por company_id (repositorios, page, thread, find, plantillas) y el revisor no encontró fuga por lectura, pero no hay prueba para: plantilla de otra empresa en POST messages (type=template), reintento de un mensaje de otra conversación/empresa, oportunidad o cliente de otra empresa en PUT opportunity (el test usa un UUID inexistente), ni paginación (page / page_size, _Rows) del listado.

## Expected behavior
Pruebas que fijen: plantilla ajena → 404; retry con message_id de otra conversación → 404; oportunidad real de otra empresa → 404; page=2 y count correctos.

## Actual behavior
Esos caminos no tienen verificación automática; una regresión en filtros por empresa no se detectaría.

## Evidence
`grep` de test_api_inbox.py: test_other_company_never_sees_or_changes_a_conversation solo prueba conversación ajena; test_closed_or_foreign_opportunity_cannot_be_linked usa `00000000-0000-0000-0000-000000000009`; ninguna prueba usa `page=`/`page_size=`.


## Resolution
Pruebas de plantilla, mensaje y oportunidad ajenos y de paginación.
