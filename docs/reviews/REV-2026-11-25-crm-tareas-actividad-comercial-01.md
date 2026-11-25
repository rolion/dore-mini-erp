# REV-2026-11-25-crm-tareas-actividad-comercial-01: Completar una tarea con actividad no valida que el cliente siga activo (INV-07)

**Status:** Resolved (corregido en delivery-build tras el Quality Gate; ver commit)
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-25-crm-tareas-actividad-comercial.md (v1)
**Spec reference:** INV-07, AC-03
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
TaskService.complete crea la actividad directamente con Activity.create y no pasa por RelatedEntities.require, a diferencia de ActivityService.create.

## Expected behavior
INV-07: no se crean actividades para un cliente inactivo. Si el cliente se desactiva despues de crear la tarea, completarla con actividad debe responder 409 customer_inactive (y no completar nada).

## Actual behavior
Se completa la tarea y se registra una actividad sobre un cliente inactivo (la tarea pendiente si es gestionable, pero la actividad nueva no deberia permitirse). Ninguna prueba cubre este caso.

## Evidence
backend/modules/crm/application/task_services.py (complete, lineas ~99-112): no hay llamada a self.related.require(...). Contraste: backend/modules/crm/application/activity_services.py create(): self.related.require(customer_id, opportunity_id). En backend/modules/crm/tests/test_api_tasks.py no existe prueba que desactive el cliente y complete con actividad (grep 'customer_inactive' solo aparece en test_inactive_customer_and_closed_opportunity_conflict y test_list_requires_one_entity_and_inactive_customer_rejected).
