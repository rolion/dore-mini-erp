# REV-2026-11-25-crm-tareas-actividad-comercial-02: El historial de actividad del dialogo solo muestra la primera pagina (20) sin paginar

**Status:** Resolved (corregido en delivery-build tras el Quality Gate; ver commit)
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-25-crm-tareas-actividad-comercial.md (v1)
**Spec reference:** AC-10, UI-04
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
ActivityDialogComponent.loadHistory llama a CrmActivitiesApiService.list(related) con page=1 y pageSize=20 por defecto, muestra el total en el encabezado «Historial (N)» pero no ofrece paginacion ni «ver mas».

## Expected behavior
UI-04/DDR: «historial de actividad de esa entidad (mas reciente primero)»; la persona debe poder consultar toda la actividad de un cliente u oportunidad.

## Actual behavior
Con mas de 20 actividades, el encabezado dice (N) pero solo se listan las 20 mas recientes; las anteriores son inaccesibles desde la UI. No hay prueba Karma con mas de una pagina.

## Evidence
frontend/panel_admin/src/app/features/crm/services/crm-activities-api.service.ts: list(related, page = 1, pageSize = 20). frontend/panel_admin/src/app/features/crm/components/activity-dialog/activity-dialog.component.ts loadHistory(): this.api.list(this.related) y history = page.results. activity-dialog.component.html: sin ngb-pagination ni boton de carga adicional.
