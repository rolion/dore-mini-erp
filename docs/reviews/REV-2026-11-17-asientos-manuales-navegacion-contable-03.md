# REV-2026-11-17-asientos-manuales-navegacion-contable-03: Enlaces antiguos a /accounting/settings?tab=... caen en Clasificaciones sin aviso

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-17-asientos-manuales-navegacion-contable.md (v1)
**Spec reference:** AC-09 (no perder funcionalidad de Configuración)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build (frontend)

## Description
AccountingSettingsComponent ahora solo conoce las pestañas classes y periods; cualquier ?tab=methods|expenses|cutoff|accounts|classifications de marcadores o enlaces externos abre Clasificaciones contables sin redirigir a la pantalla heredada o de Cuentas.

## Expected behavior
Los valores antiguos de ?tab redirigen a /settings/legacy?tab=... o a /accounts.

## Actual behavior
initialTab() devuelve 'classes' para cualquier valor desconocido. Los enlaces internos (classification-hint, cobertura) ya fueron actualizados, por lo que solo afecta marcadores.

## Evidence
accounting-settings.component.ts: this.tabs.find(...) ?? 'classes'.
