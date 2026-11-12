# REV-2026-11-12-simplificar-flujo-proforma-cobro-04: El texto «Saldo por cobrar» del diálogo de cobro sigue bajo 4.5:1 en tema oscuro

**Status:** Resolved (corregido el 2026-11-12 y cubierto por prueba de componente; sin reverificar en navegador)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-12-simplificar-flujo-proforma-cobro.md (v1)
**Spec reference:** AC-13 / NFR (contraste ≥ 4.5:1 en claro y oscuro); REV-02 (descripción: también citaba `<small class="text-muted">`)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
La corrección de REV-02 cambió solo el botón «Distribuir por tratamiento» (ahora `btn btn-sm btn-light`). El `<small class="text-muted">` de «Saldo por cobrar» en `payment-dialog.component.html` (y los `text-muted` de la columna de pieza) conserva el color del tema claro sobre el fondo oscuro del diálogo.

## Expected behavior
Texto pequeño con contraste ≥ 4.5:1 en tema oscuro dentro del diálogo.

## Actual behavior
En tema oscuro el texto es `rgb(100,120,154)` sobre `rgb(22,25,42)`: 3.89:1 (sigue legible, pero por debajo del umbral). Es el mismo valor que ya se midió en la ronda 1 y que REV-02 mencionaba.

## Evidence
Navegador, tema Oscuro (panel de ajustes), diálogo «Registrar cobro · ODO-000001», estilos computados y luminancia WCAG: `muted: rgb(100, 120, 154) rgb(22, 25, 42) 3.89`; en el mismo diálogo: enlace/botón 13.95, atajo «50 %» 6.73, etiquetas 6.73. Ajuste sugerido: en el SCSS del diálogo, bajo `:host-context(.dark)`, fijar `.text-muted` a un color con ≥ 4.5:1 (p. ej. el mismo `#96a2b4` ya usado).
