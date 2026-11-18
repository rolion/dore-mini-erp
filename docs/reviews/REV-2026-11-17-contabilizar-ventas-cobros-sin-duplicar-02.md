# REV-2026-11-17-contabilizar-ventas-cobros-sin-duplicar-02: Deshabilitar Contabilidad levanta el bloqueo de total y de cancelación de un pedido reconocido

**Status:** Resolved (documentado en ADR, decisión 10; aceptado por la persona)
**Severity:** Medium
**Category:** ARCHITECTURE
**Related plan:** docs/plans/PLAN-2026-11-17-contabilizar-ventas-cobros-sin-duplicar.md (v1)
**Spec reference:** ADR §2-§6
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
`is_recognized` devuelve False con el módulo deshabilitado: se puede cambiar el total o cancelar un pedido ya reconocido sin reversión, y los cobros no se contabilizan.

## Expected behavior
Documentar la consecuencia en el ADR (módulo deshabilitado = Ventas independiente) o decidir otra política.

## Actual behavior
Al rehabilitar, el libro queda inconsistente con el pedido. Es coherente con «módulo deshabilitado = nada cambia», pero no está documentado ni probado.

## Evidence
`adapters.py` `is_recognized` (`self._enabled() and ...`). Hallado por el Quality Gate (subagente aislado, 2026-11-17); suite backend 1986 OK y frontend 1574 OK.
