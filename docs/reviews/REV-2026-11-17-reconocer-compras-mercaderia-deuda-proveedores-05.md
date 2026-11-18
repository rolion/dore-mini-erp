# REV-2026-11-17-reconocer-compras-mercaderia-deuda-proveedores-05: Las alertas del diálogo de pago usan el naranja con texto blanco de la plantilla (contraste AA)

**Status:** Resolved
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-17-reconocer-compras-mercaderia-deuda-proveedores.md (v2)
**Spec reference:** UI-04, DDR dialogo-de-pago-asiento-previsto-y-vinculo (Componentes/patrones: «alerta de Contabilidad en estilo tenue, contraste AA, SCSS @use del parcial alert-warning»), docs/design/design-system.md secciones 7 y 8
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`payment-dialog.component.html` agrega dos `<div class="alert alert-warning">` (`alert-posting-issues` con `alert-link`, y `preview-issues`). El componente no tiene hoja de estilos (el directorio solo tiene .html/.ts/.spec.ts), así que no importa `accounting/components/_alert-warning.scss` ni sobrescribe `.alert-link`. La plantilla pinta `alert-warning` en naranja (`variable.color(warning)`, #ffa426) con `color: #fff`; el propio `reception-form.component.scss` documenta que ese estilo tiene contraste bajo y que el `.alert-link` se vuelve blanco. Es el mismo problema que el DDR manda evitar.

## Expected behavior
Las alertas de configuración contable del diálogo de pago son legibles en tema claro y oscuro (AA), con el mismo parcial que Contabilidad y Recepciones.

## Actual behavior
Texto blanco sobre naranja (~2:1) en los avisos de faltantes de configuración y del asiento previsto; el enlace «Ir a la configuración de Compras» hereda el color blanco de la plantilla.

## Evidence
```
$ ls frontend/panel_admin/src/app/features/purchases/components/payment-dialog/
payment-dialog.component.html  payment-dialog.component.spec.ts  payment-dialog.component.ts
$ grep -n "alert-warning" payment-dialog.component.html
alert alert-warning ... data-testid="alert-posting-issues"
alert alert-warning mt-2 mb-0 ... data-testid="preview-issues"
$ sed -n 65,67p src/assets/scss/override/_alert.scss   ->  &.alert-warning { background-color: variable.color(warning); }  (y .alert { color: #fff })
```
La revisión visual en navegador no se hizo (no verificada); la conclusión sale del código y del comentario de reception-form.component.scss.

## Resolution
Resuelto: el diálogo usa el componente compartido `app-posting-issues-alert` (estilo tenue con contraste AA y tokens del tema oscuro de SRV-01) para los avisos de configuración.
