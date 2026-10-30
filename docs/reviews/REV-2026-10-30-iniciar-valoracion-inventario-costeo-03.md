# REV-2026-10-30-iniciar-valoracion-inventario-costeo-03: El encabezado muestra «1. Conciliar» mientras carga

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-30-iniciar-valoracion-inventario-costeo.md (v1)
**Spec reference:** UI-02 / DDR (estado cargando)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Revisión visual en navegador (ancho ≈ 586 px, backend y frontend locales).

## Expected behavior
Mientras se consulta si ya hay adopción, el título de la tarjeta debería ser neutro («Valoración inicial»).

## Actual behavior
Con la empresa ya adoptada, al recargar `inventory/valuation` el título muestra «Valoración inicial › 1. Conciliar» junto a «Cargando…» y luego cambia a «Valoración inicial adoptada» (`valuation.component.html`, `@switch (phase)` cae en el `@default` del paso).

## Evidence
Captura tras `navigate` a `/pocketbiz/inventory/valuation`: título «Valoración inicial › 1. Conciliar» con el texto «Cargando…».
