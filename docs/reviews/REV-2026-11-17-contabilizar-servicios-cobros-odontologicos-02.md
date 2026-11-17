# REV-2026-11-17-contabilizar-servicios-cobros-odontologicos-02: Mensaje de rectificación no veraz para líneas solo prestadas

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-17-contabilizar-servicios-cobros-odontologicos.md (v1)
**Spec reference:** INV-07, AC-11
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
quotations y dentistry decían «La línea tiene cobros registrados» aunque la línea solo estuviera prestada.

## Expected behavior
Cada rama contable y mensaje relevante cubierto y veraz; componentes y estilos coherentes con el sistema de diseño.

## Actual behavior
Ver descripción.

## Evidence
Quality Gate (subagente aislado, 2026-11-17). Resuelto: el mensaje es ahora «La línea tiene cobros o ya fue prestada: no se puede rectificar.» en ambos módulos.
