# El enlace «Reintentar» del aviso de error de Saldos es casi ilegible en tema claro (contraste ~1,3:1)

**Status:** Open
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-16-mostrar-sumas-saldos-cuentas-contables.md (v1)
**Spec reference:** DDR pantalla de saldos (estado de error); design-system.md §8 (legibilidad / contraste)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
En el estado de error de `/pocketbiz/accounting/balances` (API caída), el botón `btn btn-link` «Reintentar» dentro de `alert alert-danger` hereda el azul de enlace del template (`rgb(22,119,255)`) sobre el fondo rojo de la alerta (`rgb(252,84,75)`): contraste aproximado 1,3:1 en tema claro. En tema oscuro el enlace se ve blanco/subrayado y es legible. El patrón `alert-danger` + `btn-link` se repite en otras pestañas del módulo `accounting`, por lo que probablemente es un problema transversal y no solo de esta pantalla.

## Expected behavior
La acción de reintento legible en ambos temas (p. ej. `alert-link` o texto heredado con subrayado).

## Actual behavior
Texto «Reintentar» azul sobre rojo en tema claro a 390, 800 y 1440 px.

## Evidence
Navegador integrado con el backend detenido: `getComputedStyle` del `[data-testid=retry]` → color `rgb(22, 119, 255)`, fondo de la alerta `rgb(252, 84, 75)`, tema claro (`body.light`). Capturas a 390/800/1440 px en claro: enlace azul de bajo contraste; en oscuro: legible.
