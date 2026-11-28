# REV-2026-11-28-crm-bandeja-whatsapp-business-03: Diálogo «Vincular contacto» no ofrece «Crear prospecto» (UI-04 / DDR)

**Status:** Closed (verificado en 2º Quality Gate)
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-28-crm-bandeja-whatsapp-business.md (v1)
**Spec reference:** PLAN UI-04 («Vincular contacto (cliente/prospecto/crear prospecto)»); DDR «Acciones en la cabecera»
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El plan y el DDR piden que, si el contacto no existe, el diálogo permita crear un prospecto (reutilizando lead-dialog) y vincularlo. El diálogo implementado solo busca cliente o prospecto existentes y permite quitar el contacto. La desviación no figura en «Desviaciones respecto al plan» del TASK (solo se documentan 3, ninguna sobre esto).

## Expected behavior
Opción «Crear prospecto» en el diálogo (o desviación documentada y aceptada).

## Actual behavior
Una conversación de un teléfono desconocido no puede vincularse a un contacto nuevo sin salir de la bandeja; tampoco se puede usar «Crear oportunidad» sin contacto previo (el backend responde 400).

## Evidence
`grep -n "lead|Lead|crear" inbox-contact-dialog/inbox-contact-dialog.component.html` solo devuelve el radio "prospecto" (existente); ninguna llamada a creación de prospecto en inbox-contact-dialog.component.ts (solo CrmLeadsApiService para buscar). Sección «Desviaciones» del TASK enumera (1) endpoint extra, (2) select de asignación, (3) hilo completo en cada consulta.


## Resolution
Botón «Crear prospecto» en el diálogo de contacto (reutiliza `lead-dialog`) + prueba.
