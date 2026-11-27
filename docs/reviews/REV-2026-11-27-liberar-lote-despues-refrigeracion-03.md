# REV-2026-11-27-liberar-lote-despues-refrigeracion-03: El ajuste de horas no tenía acceso desde la UI

**Status:** Resolved
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-27-liberar-lote-despues-refrigeracion.md (v1)
**Spec reference:** AC-07, UI-04
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Hallado en la revisión visual con la app levantada: el campo «Horas mínimas de refrigeración» solo era alcanzable por la API; no existía la ruta `production/settings` ni la entrada de menú, por lo que la persona no podía configurarlo en Ajustes → Producción.

## Expected behavior
El mínimo se configura en Ajustes → Producción (AC-07, UI-04).

## Actual behavior
Sin ruta ni menú; la pantalla de ajustes del módulo no se podía abrir.

## Evidence
`app.routes.ts` solo tenía `production/recipes` y `production/orders`; `assets/data/routes.json` no tenía `/pocketbiz/production/settings` (Quality Gate ciclo 2 no lo detectó porque no se probó con la app levantada).

## Resolución
Ruta `production/settings` (`settingsModule: 'production'`), entrada «Configuración» bajo Producción, título «Producción» y claves i18n es/en/pt; `sidebar-menu.spec` actualizado. Verificado en el navegador: la pantalla muestra el campo con unidad «h» y «Valor predeterminado: 12 h».
