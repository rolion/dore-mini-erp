# REV-2026-10-14-landing-pocketbiz-rutas-01: `npm run build` (producción) falla por presupuesto de estilos de la landing

**Status:** Open
**Severity:** High
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-13-landing-pocketbiz-rutas.md (v2)
**Spec reference:** AC-17 ("`npm run lint` y `npm run build` pasan"); Non-functional: rendimiento
**Plan mode:** COMPLETO
**Suggested owner:** delivery-engineer

## Description
`features/landing/pages/landing/landing.component.scss` pesa 4,96 kB y supera el `maximumError` de `anyComponentStyle` (4 kB, `angular.json:75-77`). El build de producción (el predeterminado de `ng build`, que es lo que ejecuta `npm run build`) termina con "Application bundle generation failed". La verificación propia del engineer solo corrió `ng build --configuration development`, que no aplica presupuestos.

## Expected behavior
AC-17: `npm run build` pasa.

## Actual behavior
El build de producción falla; no se puede generar el artefacto desplegable.

## Evidence
```
$ npx ng build        # = npm run build
Application bundle generation failed. [13.354 seconds]
▲ [WARNING] src/app/features/landing/pages/landing/landing.component.scss exceeded maximum budget. Budget 2.00 kB was not met by 2.96 kB with a total of 4.96 kB.
X [ERROR] src/app/features/landing/pages/landing/landing.component.scss exceeded maximum budget. Budget 4.00 kB was not met by 963 bytes with a total of 4.96 kB.
```
Sugerencia (no prescriptiva): reducir/dividir el SCSS (p. ej. mover reglas compartidas a variables/mixins, o partir en subcomponentes como contemplaba el plan) en vez de subir el presupuesto global.
