# REV-2026-11-16-configurar-asientos-automaticos-modulo-10: Textos de apoyo del panel con `text-muted` no alcanzan el contraste AA (2.5:1 claro, 3.89:1 oscuro)

**Status:** Resolved
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-16-configurar-asientos-automaticos-modulo.md (v3)
**Spec reference:** AC-14, design-system.md §8 (legibilidad en tema claro y oscuro)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Tercera pasada, navegador integrado, las cuatro pantallas de configuración. En `posting-config-panel.component.html` el párrafo de introducción (`<p class="text-muted mb-3">` bajo «Asientos automáticos») y el vacío «sin categorías» (`<p class="text-muted" data-testid="no-categories">`) usan `text-muted`.

## Expected behavior
Texto normal con contraste mínimo 4.5:1 en ambos temas (el resto del panel usa `text-body-secondary`, que sí cumple).

## Actual behavior
Medido (color de texto compuesto sobre el fondo efectivo, fórmula WCAG): intro del panel `rgb(152,166,173)` sobre blanco = 2.50:1 en tema claro; en tema oscuro (selector real «Oscuro» del panel de ajustes) = 3.89:1. Para comparar, `.text-body-secondary` da 6.78:1 (claro) y 6.73:1 (oscuro). Los estados propios sí pasan: `.posting-warn` 19.11:1 claro / 4.53:1 oscuro (en filas de rol 6.73:1), `alert-warning` 14.04:1 claro / 4.53:1 oscuro, `alert-success` 10.35:1, `alert-info` 7.65:1, «Guardado ✓» 21:1 claro / 6.73:1 oscuro. Nota: el mensaje de error de fila (`text-danger`, plantilla) mide 3.23:1 sobre blanco (5.39:1 en oscuro); es el color estándar de la plantilla, se reporta solo como observación.

## Evidence
Mediciones por JS en `/es/pocketbiz/{sales,purchases,inventory,expenses}/settings` a 1440 px y 375 px; la intro mide 2.5 (claro) y 3.89 (oscuro) en las cuatro pantallas. `.posting-warn` en oscuro (4.53) queda justo sobre el umbral: conviene vigilarlo si cambia el fondo.

## Resolution
La intro y el vacío del panel usan `text-body-secondary` en lugar de `text-muted`.
