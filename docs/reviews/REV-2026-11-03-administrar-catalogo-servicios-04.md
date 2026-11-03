# REV-2026-11-03-administrar-catalogo-servicios-04: Nombres recortados en tabla móvil

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-02-administrar-catalogo-servicios.md (v3)
**Spec reference:** UI-01
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
En el listado de Servicios a 390×844, los nombres de la tabla se muestran truncados. La tabla permite desplazamiento horizontal, pero la lectura completa de cada nombre exige interactuar con un control pequeño.

## Expected behavior
Los nombres de servicios deben ser legibles en móvil o el mecanismo para revelar su contenido debe ser evidente y fácil de usar.

## Actual behavior
El revisor visual observó `BRACKETES` como `BRA...` y `limpieza dental` como `lim...` en el ancho móvil.

## Evidence
Inspección independiente en navegador de `/pocketbiz/catalog/services` a 390×844, tema claro y oscuro; desktop 1440×900 sin este problema. No hubo solapamiento de controles. Karma completo 1118/1118 y build pasaron. Hallazgo de usabilidad Low que no bloquea el Quality Gate.
