# REV-2026-11-16-configurar-asientos-automaticos-modulo-03: Vista previa Debe/Haber se recorta a 375 px y hay trazos de borde sueltos

**Status:** Resolved
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-16-configurar-asientos-automaticos-modulo.md (v1)
**Spec reference:** AC-14, UI-01, design-system.md §8
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Revisión visual en el navegador integrado con viewport emulado 375x812 y clase de tema oscuro en body, en /es/pocketbiz/sales/settings pestaña «Asientos automáticos».

## Expected behavior
A 375 px las tarjetas de «Asientos previstos» muestran el texto completo sin scroll horizontal interno, y las filas apiladas (inventory-table) no muestran bordes parciales.

## Actual behavior
En la tarjeta «Cobrar una venta» la celda «Según el método de pago» se corta ("Según el método de…") y aparece una barra de desplazamiento horizontal dentro de la tarjeta; en las filas de cuentas y en la tabla de eventos se ven trazos de borde cortos bajo las etiquetas (efecto del estilo inventory-table apilado). El documento no desborda (scrollWidth=clientWidth=375). Es aspecto visual, no pérdida de funcionalidad.

## Evidence
Captura móvil/oscuro del panel de Ventas (tabla de la tarjeta recortada). Escritorio (viewport 1024 px, tema claro) en /expenses/settings: aviso azul tenue, filas con select + Guardar, guardado persistente («Guardado ✓»), sin defectos. Nota: tema oscuro emulado cambiando clases del body (dark), no con el conmutador de la app; 1440 px no probado (el panel del navegador quedó en 1024 px).

## Resolution
`posting-config-panel.component.scss`: la etiqueta de fila (`th`) se apila en móvil, la tabla de vista previa parte el texto (`min-width: 0`, `overflow-wrap`) y la columna Lado se reduce. Pendiente de confirmar visualmente en la segunda pasada.
