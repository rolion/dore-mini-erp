# REV-2026-10-30-iniciar-valoracion-inventario-costeo-01: Enlace «Valoración» dentro de un tablist sin rol de pestaña

**Status:** Open
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-10-30-iniciar-valoracion-inventario-costeo.md (v1)
**Spec reference:** UI-01; design-system sección 7 (accesibilidad mínima) y sección 8
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El enlace de navegación a Valoración se agregó como `<li class="nav-item"><a class="nav-link">` dentro de `<ul role="tablist">`, junto a pestañas reales (`<button role="tab">`).

## Expected behavior
Los hijos de un `role="tablist"` deben ser pestañas (`<li role="presentation">` envolviendo un `role="tab"`); un enlace que navega a otra ruta no es una pestaña, por lo que debería quedar fuera del tablist (p. ej. un botón/enlace en el encabezado de la tarjeta) o conservar la semántica de enlace sin romper el tablist.

## Actual behavior
El `<li>` no tiene `role="presentation"` y el `<a>` no tiene rol de pestaña ni `aria-controls`; los lectores de pantalla anuncian una pestaña sin panel asociado.

## Evidence
frontend/panel_admin/src/app/features/inventory/pages/inventory-configuration/inventory-configuration.component.html líneas 20-35 (`@if ((enabledKeys$ | async)?.has('costing'))`). Inspección solo de código; navegador no verificado.
