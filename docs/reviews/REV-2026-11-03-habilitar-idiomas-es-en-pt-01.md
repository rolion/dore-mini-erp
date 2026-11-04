# REV-2026-11-03-habilitar-idiomas-es-en-pt-01: Texto visible en español hardcodeado en plantillas del producto

**Status:** Resolved (corregido en delivery-build; verificación de la corrección sin Quality Gate aislado nuevo)
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-03-habilitar-idiomas-es-en-pt.md (v1)
**Spec reference:** AC-08; Non-functional requirements (sin texto visible hardcodeado)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Quedan literales en español dentro de plantillas de pantallas alcanzables desde el menú (inventario y ventas), incluido texto solo para lector de pantalla.

## Expected behavior
Todo texto visible o accesible sale de claves es/en/pt; en inglés/portugués no debe aparecer español mezclado.

## Actual behavior
En en/pt estas cadenas siguen en español: la nota de pendientes de valoración (`producto está` / `productos están` pasado como parámetro), `negativo` y `entrada`/`salida` en spans `visually-hidden`. `npm run i18n:check` no lo detecta porque solo valida claves usadas, no literales.

## Evidence
```
features/inventory/pages/valuation/valuation.component.html:220: p1: (pendingCount === 1 ? 'producto está' : 'productos están')
features/sales/components/delivery-dialog/delivery-dialog.component.html:70: <span class="visually-hidden">negativo</span>
features/inventory/pages/adjustment-list/adjustment-list.component.html:110: <span class="visually-hidden">({{ row.kind === 'in' ? 'entrada' : 'salida' }})</span>
```
