# REV-2026-10-28-ajustar-existencias-con-motivo-03: Detalles visuales leves en la lista móvil y en los avisos

**Status:** Fixed (pendiente de verificación en el ciclo 3)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-28-ajustar-existencias-con-motivo.md (v1)
**Spec reference:** UI-01, UI-03 (DDR: lista apilada en móvil, avisos de revisión)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Hallados en la revisión visual en navegador (2026-10-28, escritorio 1440 px, móvil 375 px, tema claro y oscuro) sobre una base aislada con datos de prueba.

1. En móvil la tabla apilada de `adjustment-list` deja «Sistema», «Contado» y «Diferencia» alineados a la derecha (`text-end`) mientras el resto de filas va a la izquierda.
2. Los avisos `alert-warning` (saldo cambiado) y `alert-info` («Sin diferencia») de la plantilla llevan texto blanco sobre ámbar/celeste: contraste justo. Es el estilo de la plantilla, no un color propio.

## Expected behavior
1. En móvil todas las celdas apiladas se alinean igual; la alineación a la derecha solo desde 768 px (`text-md-end`).
2. Texto de los avisos con contraste suficiente.

## Actual behavior
Ver Description. Sin scroll horizontal (`scrollWidth` 375 = `innerWidth` 375); sin otros desvíos del sistema de diseño.

## Evidence
Capturas del navegador integrado: lista a 375 px (celdas numéricas a la derecha), aviso ámbar «El saldo cambió de 37 a 35…» y aviso celeste «Sin diferencia…». Archivos: `frontend/panel_admin/src/app/features/inventory/pages/adjustment-list/adjustment-list.component.html` (clases `text-end`).
