# REV-2026-11-27-consultar-ordenes-seguimiento-estado-06: Contraste de textos de apoyo con `text-muted`

**Status:** Open
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-27-consultar-ordenes-seguimiento-estado.md (v2)
**Spec reference:** UI-04 / design-system sección 8 (accesibilidad)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build (opcional; o decisión global del sistema de diseño)

## Description
Las fechas de las etapas del stepper, los hints de las cifras clave y el subtítulo usan `text-muted`. La plantilla fuerza `.text-muted { color: rgb(152,166,173) !important }`, que sobrescribe `--bs-secondary-color`.

## Expected behavior
Contraste mínimo 4.5:1 en texto.

## Actual behavior
Medido en el navegador sobre `.order-step-date.text-muted`: 2.50:1 en tema claro y 3.89:1 en oscuro. Es la convención de todo el sistema (`design-system.md` indica `small.text-muted`), no un defecto exclusivo de esta pantalla.

## Evidence
`order-detail.component.html:17`, `:43`, `:58`, `:67` (Quality Gate aislado, 2026-11-27). Posible solución: usar `--bs-secondary-color` en esas clases, o decidir globalmente en el sistema de diseño.
