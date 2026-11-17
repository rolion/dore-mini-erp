# REV-2026-11-17-contabilizar-servicios-cobros-odontologicos-06: Doble `role="alert"` y fecha con formato fijo en el diálogo de prestación

**Status:** Resolved
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-17-contabilizar-servicios-cobros-odontologicos.md (v1)
**Spec reference:** UI-02
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Un error de fecha puede anunciarse dos veces (campo y alerta general); «Prestado el» usa `dd/MM/yyyy` sin depender del idioma.

## Expected behavior
Cada rama contable y mensaje relevante cubierto y veraz; componentes y estilos coherentes con el sistema de diseño.

## Actual behavior
Ver descripción.

## Evidence
Quality Gate (subagente aislado, 2026-11-17). Menor; pendiente de la revisión visual.

Resuelto: el error de fecha se anuncia solo en el campo (`role="alert"`) y la alerta general se oculta en ese caso. El formato `dd/MM/yyyy` se mantiene a propósito: es el que usa toda la página de Cobros.
