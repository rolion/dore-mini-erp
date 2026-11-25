# REV-2026-11-25-crm-tareas-actividad-comercial-04: completed_at se conserva al archivar: contradice INV-03 sin actualizar la Specification

**Status:** Resolved (2026-11-25: el usuario aprobó conservar la fecha; INV-03 enmendada en PLAN v3)
**Severity:** Low
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-11-25-crm-tareas-actividad-comercial.md (v1)
**Spec reference:** INV-03, API contract
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
La implementacion conserva completed_at al archivar una tarea hecha (y el CHECK de BD crm_task_completed_coherent permite archived con o sin fecha). INV-03 dice que completed_at es nulo en todos los estados distintos de done. El TASK lo registra como desviacion «sin cambiar Specification».

## Expected behavior
Specification y codigo coherentes: o INV-03 se enmienda (completed_at se conserva en archived si la tarea estaba hecha) o archive() limpia la fecha.

## Actual behavior
INV-03 queda desactualizado: una tarea archivada devuelve completed_at no nulo si estaba hecha y nulo si estaba cancelada. No afecta ningun AC ni se puede observar desde la UI (las archivadas no se listan), pero es un cambio de invariante, no solo de implementacion.

## Evidence
backend/modules/crm/domain/task.py archive(): solo cambia self.status = ARCHIVED. backend/modules/crm/infrastructure/django/models.py: Q(status__in=['pending','cancelled'], completed_at__isnull=True) | Q(status='done', completed_at__isnull=False) | Q(status='archived'). docs/tasks/TASK-crm-tareas-actividad-comercial.md ## Implementacion: «completed_at se conserva al archivar una tarea hecha (INV-03 lo daba nulo en los demas estados)».
