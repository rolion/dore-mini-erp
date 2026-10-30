# REV-2026-10-30-habilitar-produccion-y-costeo-03: El diálogo decide la adopción por clave fija y muestra la fecha del cliente

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-30-habilitar-produccion-y-costeo.md (v1)
**Spec reference:** UI-02; AC-05; API-01
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`ModuleConfirmDialogComponent.recordsAdoption` es `this.module.key === 'costing'` (el comentario dice «todo módulo que fija fecha de adopción»), y `today` es `new Date()` del navegador. La API no expone `records_adoption`, así que la regla de negocio queda duplicada en el cliente; y la fecha mostrada («Hoy (dd/MM/yyyy)») puede diferir de la `adopted_at` real del servidor (zona horaria/reloj del cliente).

## Expected behavior
El diálogo deriva el aviso de un dato del servidor (o de un único lugar compartido) y la fecha mostrada coincide con la zona de la empresa; cualquier otro módulo con `records_adoption` en el futuro mostraría el aviso sin tocar el frontend.

## Actual behavior
Solo `costing` activa el aviso; la fecha es la local del cliente. Sin impacto funcional hoy (un único módulo y fecha informativa antes de confirmar).

## Evidence
`frontend/panel_admin/src/app/features/settings/components/module-confirm-dialog/module-confirm-dialog.component.ts` (`get recordsAdoption`, `get today`) y `.html` (`@if (isEnable && recordsAdoption)`).
