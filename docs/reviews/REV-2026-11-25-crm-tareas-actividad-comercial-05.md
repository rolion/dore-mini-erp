# REV-2026-11-25-crm-tareas-actividad-comercial-05: Cancelar y archivar tareas se ejecutan sin confirmacion (DDR pide patron de confirmacion)

**Status:** Open (Low; aceptado, listado en Known limitations)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-25-crm-tareas-actividad-comercial.md (v1)
**Spec reference:** UI-02, DDR (Componentes/patrones elegidos)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
En «Por contactar», los botones Cancelar y Archivar llaman directamente a la API.

## Expected behavior
DDR: «cancelar tarea usa el patron de confirmacion de §5 sin motivo obligatorio» (dialogo de accion irreversible). Archivar es terminal (oculta la tarea sin camino de vuelta en la UI).

## Actual behavior
Un clic accidental cancela o archiva la tarea al instante; archivar es irreversible desde la UI porque las archivadas no se muestran. La desviacion no esta en la lista de «Desviaciones» del TASK.

## Evidence
frontend/panel_admin/src/app/features/crm/pages/crm-task-list/crm-task-list.component.ts: cancel(task) { this.run(this.api.cancel(task.id), 'CRM.TASK_LIST.CANCELADA_OK'); } y archive(task) igual, sin this.modal.open. grep -n confirm sobre crm-task-list.component.spec.ts -> sin resultados.
