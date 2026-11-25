# REV-2026-11-25-crm-tareas-actividad-comercial-07: Desviaciones del plan/DDR no registradas: relacionado solo cliente en la lista, activity-history, compacta bajo md

**Status:** Open (Low; aceptado, listado en Known limitations)
**Severity:** Low
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-11-25-crm-tareas-actividad-comercial.md (v1)
**Spec reference:** UI-01, UI-02, UI-04, DDR, Files/components affected
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
Varias diferencias frente al PLAN/DDR no estan en la lista de desviaciones del TASK o requieren actualizar el DDR.

## Expected behavior
El DDR (Estado: Propuesto) y el PLAN reflejan lo construido, o la desviacion queda justificada: (a) dialogo Tarea con relacionado «cliente u oportunidad»; (b) componente activity-history autonomo; (c) variante compacta bajo lg; (d) test_api_activities.py y protocolos en ports.py.

## Actual behavior
(a) «Nueva tarea» desde la lista solo permite elegir cliente (TaskDialogComponent choosesRelated es un selector de clientes); las tareas de oportunidad solo se crean desde la tarjeta del Kanban (esta si esta en el TASK). (b) No existe activity-history: el historial esta embebido en activity-dialog. (c) La tabla se apila bajo md (768px), no lg (992px). (d) Las pruebas de actividad estan en test_api_tasks.py y no hay protocolos nuevos en ports.py (esto ultimo si esta en el TASK). Evaluacion: ninguna cambia un AC ni una invariante (AC-09/AC-10 se cumplen), pero (a) y (c) contradicen texto del DDR y el DDR no se actualizo.

## Evidence
git diff 936c3a5e..HEAD --stat: no existen components/activity-history ni tests/test_api_activities.py. crm-task-list.component.scss: @media (max-width: 767.98px). docs/design/DDR-crm-tareas-actividad-comercial-por-contactar-y-actividad.md: «variante compacta bajo lg» y «relacionado (cliente u oportunidad, no editable al editar)».
