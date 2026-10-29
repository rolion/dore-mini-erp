# REV-2026-10-29-politica-stock-negativo-04: UI-02: se creó SettingConfirmDialogComponent en vez de reutilizar ModuleConfirmDialogComponent y la desviación no está documentada

**Status:** Clarified (ver TASK, desviación 5)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-29-politica-stock-negativo.md (v1)
**Spec reference:** UI-02; DDR (Confirmación al habilitar); TASK > Implementación > Desviaciones
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
UI-02 y el DDR indican reutilizar `ModuleConfirmDialogComponent`. Ese componente está acoplado a habilitar/deshabilitar módulos (usa `ModulesService`), por lo que la creación de un diálogo nuevo es razonable, pero no figura en la lista de desviaciones del TASK. Además el mapa `ENABLE_CONFIRMATIONS` vive en el componente (deuda ya reconocida).

## Expected behavior
Reutilizar el diálogo existente o registrar la desviación (nuevo `setting-confirm-dialog`) en el TASK y actualizar el DDR.

## Actual behavior
Componente nuevo `features/settings/components/setting-confirm-dialog/*` con título/mensaje/botón idénticos al DDR, con specs; sin registro de la desviación.

## Evidence
`git diff origin/main...HEAD --stat` lista los 3 archivos nuevos; TASK > Desviaciones enumera 4 puntos y ninguno lo menciona.
