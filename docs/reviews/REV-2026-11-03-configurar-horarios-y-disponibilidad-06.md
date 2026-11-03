# Fallan 2 pruebas Karma del menú lateral

**Status:** Open
**Severity:** High
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-03-configurar-horarios-y-disponibilidad.md (v1)
**Spec reference:** AC-04 (navegación)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Evidence

El diff añade el menú Agenda en `routes.json` sin actualizar `sidebar-menu.spec.ts`. `npm test -- --watch=false --browsers=ChromeHeadless --code-coverage` terminó con `TOTAL: 2 FAILED, 1116 SUCCESS`: `Expected 12 to be 11.` y `Expected 'agenda' to be 'personnel'.` (sidebar-menu.spec.ts:16,25); `Expected 33 to be 31.` (sidebar-menu.spec.ts:84).

Origen: tercer Quality Gate independiente sobre `7d521eb`.

Corrección implementada tras el tercer gate; pendiente de verificación en el siguiente Quality Gate.
