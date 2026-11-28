# REV-2026-11-28-crm-bandeja-whatsapp-business-06: Envío de plantilla desde la bandeja no admite variables (components)

**Status:** Closed (verificado en 2º Quality Gate)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-28-crm-bandeja-whatsapp-business.md (v1)
**Spec reference:** API-04 (components?); UI-03; AC-03
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El endpoint acepta components, pero crm-inbox-api.service.sendTemplate y la página solo envían {type, template_id}. Las plantillas con variables ({{1}}) no podrían enviarse con valores. Además la UI vuelve a pedir el hilo completo cada 10 s (sin usar after, desviación 3 documentada) y el hilo se limita a los 200 mensajes más recientes sin paginar hacia atrás.

## Expected behavior
Documentar la limitación como alcance (plantillas sin variables) o permitir completar parámetros; indicar el tope de 200 mensajes.

## Actual behavior
Plantillas con parámetros fallarían al entregarse (Meta) y quedarían failed; la limitación no figura en el TASK.

## Evidence
crm-inbox-api.service.ts: `sendTemplate` → body `{ type: 'template', template_id: templateId }`; messaging/services.py: `THREAD_LIMIT = 200`.


## Resolution
Documentado como alcance: plantillas sin variables y hilo de 200 mensajes (ver TASK).
