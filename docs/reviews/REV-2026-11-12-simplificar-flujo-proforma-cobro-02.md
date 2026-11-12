# REV-2026-11-12-simplificar-flujo-proforma-cobro-02: En tema oscuro el enlace «Distribuir por tratamiento» del diálogo de cobro es casi invisible

**Status:** Resolved (corregido el 2026-11-12; pendiente de reverificación en el segundo Quality Gate)
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-12-simplificar-flujo-proforma-cobro.md (v1)
**Spec reference:** AC-13 / NFR (contraste ≥ 4.5:1 en claro y oscuro), design-system.md §8
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`payment-dialog.component.html` usa `<button class="btn btn-link">` para «Distribuir por tratamiento» / «Volver al reparto automático» y `<small class="text-muted">` para «Saldo por cobrar». El SCSS del diálogo solo ajusta fondo, texto y borde del `dialog` en `.dark`; estos elementos conservan colores del tema claro.

## Expected behavior
Texto legible con contraste ≥ 4.5:1 en tema oscuro (el control avanzado es la única vía para repartir manualmente).

## Actual behavior
En tema oscuro el enlace `btn-link` se renderiza `rgb(37,37,37)` sobre el fondo del diálogo `rgb(22,25,42)` (≈1.14:1, prácticamente invisible); el texto `text-muted` pequeño es `rgb(100,120,154)` (≈3.89:1). Observación adicional (informativa): los `app-status-badge` no cambian con el tema oscuro (la app marca `body.dark`, no `data-bs-theme`), por lo que mantienen el tono claro (texto oscuro sobre fondo pálido; legible, pero llamativo sobre fondo oscuro). Los pares calculados de los cinco tonos dan contraste alto (entre ≈7.2 y ≈10.5) porque no varían con el tema.

## Evidence
Navegador, tema Oscuro (panel de ajustes), diálogo «Registrar cobro · ODO-000001», contrastes calculados con luminancia relativa WCAG sobre estilos computados:
`link: rgb(37, 37, 37) ... ratio vs dialog 1.14`; `muted: rgb(100, 120, 154) ... ratio vs dialog 3.89`; atajo «50 %»: `rgb(150,162,180)` ratio 6.73 (correcto).
