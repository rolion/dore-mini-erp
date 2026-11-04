# REV-2026-11-04-mejorar-ux-horarios-y-ausencias-06: Huecos de cobertura en pruebas: PUT de ausencia inexistente, fin = inicio y DOM de «Todo el día»/repetición

**Status:** Fixed (pendiente de nueva revisión)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-04-mejorar-ux-horarios-y-ausencias.md (v1)
**Spec reference:** EDGE-03, EDGE-05, AC-08, AC-10
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Las pruebas nuevas cubren AC-01..AC-12 casi por completo.

## Expected behavior
Cada EDGE tiene una prueba: EDGE-05 en PUT y DELETE, EDGE-03 con fin igual al inicio, y pruebas de DOM para los interruptores.

## Actual behavior
`test_absence_can_be_edited_and_deleted` verifica 404 solo en DELETE repetido (no PUT a id inexistente) y 400 solo con fin anterior al inicio. En el frontend `toggleAllDay()` no tiene prueba y los radios `(change)="applyRepeat()"` se prueban llamando al método, no mediante eventos del DOM. Además el TASK declara un fallo ajeno en `core/i18n/screens-i18n.spec.ts:60`; en esta revisión `npm test` terminó con 1261 de 1261 SUCCESS, así que esa nota está desactualizada.

## Evidence
Salida `TOTAL: 1261 SUCCESS` de `npm test -- --watch=false --browsers=ChromeHeadless`; lectura de `backend/modules/agenda/tests/test_api.py`.
