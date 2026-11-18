# REV-2026-11-16-configurar-asientos-automaticos-modulo-13: Faltan pruebas de los casos borde de la configuración por categoría

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-16-configurar-asientos-automaticos-modulo.md (v3)
**Spec reference:** AC-03, AC-07, AC-10, EDGE-03, INV-02
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Tercera pasada. Las pruebas pasan (1962 backend, 1572 frontend), pero el cambio v3 no cubre estos casos; los verifiqué manualmente por API y navegador y se comportan bien.

## Expected behavior
Hay prueba automática de: (1) cuenta de una categoría deshabilitada o reclasificada después de asignarla (`check_posting_ready`/`post_automatic_entry` → `account_invalid` con el nombre de la categoría); (2) aislamiento por empresa de las asignaciones de categoría (empresa B no ve ni usa las de A; hoy solo hay prueba de aislamiento para roles); (3) `ExpenseSettingsComponent` con error de carga («Reintentar») y con más de una página de categorías.

## Actual behavior
No existen. Verificación manual: cuenta «Gasto luz» deshabilitada → la fila y el aviso global la reportan por nombre; empresa B recibe `categories: []` y 400 «La cuenta no existe en esta empresa.» al usar una cuenta de A; el error de carga muestra el alert y «Reintentar» recarga.

## Evidence
`test_posting_service.py`/`test_posting_config_api.py` solo prueban categoría sin cuenta, cuenta que no es de Gastos y asignar/quitar; `expense-settings.component.spec.ts` solo el caso feliz.

## Resolution
Pruebas añadidas: cuenta de categoría deshabilitada tras asignarla (servicio y panel), aislamiento por empresa de categorías, error de carga y paginación de `ExpenseSettings`.
