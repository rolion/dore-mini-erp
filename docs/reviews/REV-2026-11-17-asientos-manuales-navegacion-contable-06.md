# REV-2026-11-17-asientos-manuales-navegacion-contable-06: Texto de «Clasificaciones contables» alude a una pestaña que ya no está en Configuración

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-17-asientos-manuales-navegacion-contable.md (v1)
**Spec reference:** AC-09
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build (frontend)

## Description
La descripción de la pestaña dice «No es lo mismo que la pestaña «Clasificaciones», que describe el motivo de un movimiento de dinero», pero esa pestaña ahora vive en Otras configuraciones.

## Expected behavior
Aclaración coherente con la pantalla actual (p. ej. indicar que está en «Otras configuraciones»).

## Actual behavior
En `/accounting/settings` el texto remite a una pestaña inexistente en esa pantalla.

## Evidence
Navegador integrado, `/pocketbiz/accounting/settings`, pestaña Clasificaciones contables, segunda línea de la descripción.

## Resolución
Corregido (2026-11-17): el texto remite a la pestaña «Clasificaciones» de «Otras configuraciones» (es/en/pt).
