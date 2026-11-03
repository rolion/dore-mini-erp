# REV-2026-11-03-configurar-horarios-y-disponibilidad-03: El formulario permite cambios durante el guardado

**Status:** Resolved
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-03-configurar-horarios-y-disponibilidad.md (v1)
**Spec reference:** AC-04
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Evidence

El callback de `save` reinicia el formulario tras el éxito. Los campos siguen editables durante la petición y los cambios posteriores al envío se pierden.
