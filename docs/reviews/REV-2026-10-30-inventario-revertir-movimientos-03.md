# REV-2026-10-30-inventario-revertir-movimientos-03: La «referencia del contramovimiento» repite la del movimiento original

**Status:** Resolved
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-10-30-inventario-revertir-movimientos.md (v1)
**Spec reference:** AC-11, AC-15, UI-01; DDR (bloque «Reversión», contramovimiento enlazado «con su referencia»)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
El contramovimiento hereda `reference` del original (`StockMovement.reverse`). En el bloque «Reversión» el enlace usa esa referencia, de modo que el original y su corrección muestran el mismo texto y no se distinguen en el enlace; en la tabla de movimientos de la recepción el enlace es el genérico «Ver contramovimiento».

## Expected behavior
La tarjeta pide mostrar la «referencia del contramovimiento» de modo identificable (p. ej. con prefijo o etiqueta «Reversión de …») o el DDR debe fijar que se muestra el tipo/fecha junto al enlace.

## Actual behavior
Mismo valor de referencia en original y contramovimiento; el vínculo sigue siendo correcto (id), solo la etiqueta es ambigua. No afecta datos.

## Evidence
- `backend/modules/inventory/domain/movement.py` en `reverse`: `reference=self.reference`.
- `backend/modules/inventory/api/movement_views.py` `_reversed_by`: `'reference': counter.reference`.
- `movement-detail.component.html`: `{{ r.reference || 'Ver contramovimiento' }}`.
