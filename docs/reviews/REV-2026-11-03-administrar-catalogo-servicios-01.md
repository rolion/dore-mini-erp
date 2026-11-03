# REV-2026-11-03-administrar-catalogo-servicios-01: Cabecera móvil del listado

**Status:** Closed
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-02-administrar-catalogo-servicios.md (v2)
**Spec reference:** AC-08 y DDR de pantallas
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
La cabecera del listado de Servicios conservaba la altura fija de 70 px del estilo compartido al envolver los filtros en móvil.

## Expected behavior
Filtros, acción de creación y texto de ayuda deben ocupar filas separadas y ser legibles a 390 px en temas claro y oscuro.

## Actual behavior
A 390×844, el botón «+» y la segunda fila de filtros se superponían con el texto sobre especialidades en ambos temas.

## Evidence
Inspección integrada en `http://127.0.0.1:4200/pocketbiz/catalog/services`, 390×844, con sesión demo; `frontend/panel_admin/src/assets/scss/override/_table.scss` fija `.ngxTableHeader { height: 70px; }`.

## Corrección delivery-build
Estilo local `service-list-header` con altura automática y espacio vertical bajo 575 px. El build de producción pasó y la inspección integrada a 390×844 confirmó que no hay solapamiento en ambos temas. La vista de escritorio a 1440×900 conserva las filas de tabla completas.
