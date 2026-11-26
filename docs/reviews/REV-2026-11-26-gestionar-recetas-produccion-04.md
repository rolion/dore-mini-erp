# REV-2026-11-26-gestionar-recetas-produccion-04: Desviaciones visuales del DDR sin declarar (ngx-datatable, foco al primer error)

**Status:** Open
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-26-gestionar-recetas-produccion.md (v1)
**Spec reference:** DDR (Componentes)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
Se usó tabla Bootstrap con `ngb-pagination` (patrón existente), sin tarjetas bajo 992 px (declarado) y sin gestión de foco al primer error (no declarado).

## Expected behavior
Desviaciones justificadas en el DDR.

## Actual behavior
Tabla Bootstrap, sin foco al error.

## Evidence
`recipe-list.component.html`, `recipe-form.component.html`.
