# REV-2026-11-17-contabilizar-ventas-cobros-sin-duplicar-16: La alerta de faltantes contables tiene contraste insuficiente

**Status:** Resolved (estilo tenue y color explícito en tema oscuro en `order-detail` y `delivery-dialog`; medido en el navegador: 17,85:1 en tema claro y 10,78:1 en oscuro, enlace incluido)
**Severity:** Medium
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-17-contabilizar-ventas-cobros-sin-duplicar.md (v3.1)
**Spec reference:** AC-17 (accesible, usable a 375 px y en tema oscuro) / UI-01, UI-02
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
La alerta que explica los faltantes de configuración contable en el detalle del pedido (cobro y entrega) y en el diálogo de entrega usa `alert alert-warning` sin el estilo tenue de Contabilidad: texto blanco sobre naranja.

## Expected behavior
Contraste AA (≥ 4.5:1) en tema claro y oscuro, como el aviso del panel de configuración (`features/accounting/components/_alert-warning.scss`, fondo suave y texto heredado).

## Actual behavior
Texto y enlace `rgb(255,255,255)` sobre `rgb(255,164,38)`: contraste **1,98:1** medido en el navegador (tema claro). El resto de la alerta se ve y el enlace abre la pestaña correcta.

## Evidence
Revisión visual (2026-11-17) sobre una copia aislada de la rama. Mismo estilo que `alert-delivered-balance` del mismo detalle (preexistente). Observado además, fuera del alcance de este PR: la tabla «Productos del pedido» desborda horizontalmente a 375 px (`scrollWidth` 805 sobre un viewport de 371).
