# REV-2026-11-15-refinar-ux-libro-entradas-enlaces-09: Prueba intermitente en core/i18n/screens-i18n.spec.ts

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-15-refinar-ux-libro-entradas-enlaces.md (v2)
**Spec reference:** Preexistente, fuera del alcance
**Plan mode:** COMPACTO
**Suggested owner:** delivery-build

## Description
Prueba intermitente en core/i18n/screens-i18n.spec.ts.

## Expected behavior
Prueba determinista.

## Actual behavior
Falló 3 de 4 ejecuciones del Quality Gate (y varias antes): `Expected 'Delivered' to be 'Entregado'` en screens-i18n.spec.ts:60. Carrera de idioma entre pruebas; no toca archivos de este diff.

## Evidence
Logs del Quality Gate (ejecuciones 1, 3 y 4) y de la sesión de build.
