# REV-2026-11-23-pedido-pantalla-unica-creacion-03: Falta el foco al selector de producto tras agregar (UI-05)

**Status:** Fixed (pendiente de re-revisión)
**Severity:** Low
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-11-23-pedido-pantalla-unica-creacion.md (v2)
**Spec reference:** UI-05
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
El plan pide foco al producto tras agregar; `addLine` solo hace `addForm.reset`. Sin prueba.

## Expected behavior
Foco programático en `#order-product` tras agregar.

## Actual behavior
Ver evidencia.

## Evidence
`order-create.component.ts` (`addLine`) no enfoca. Puede resolverse quitando esa frase de UI-05 (cambio de Specification: requiere aprobación) o implementándolo.

## Resolución
UI-05 ya no exige el foco al producto tras agregar (PLAN v2, aprobado por el usuario).
