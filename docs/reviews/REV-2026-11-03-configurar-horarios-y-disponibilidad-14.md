# El error de guardado de los diálogos no usa el estilo de alerta

**Status:** Open
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-03-configurar-horarios-y-disponibilidad.md (v1)
**Spec reference:** design-system §8 (error visible)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Evidence

El `<p data-save-error role="alert">` dentro de los diálogos se ve como texto plano con el borde de foco, sin el patrón `alert alert-danger` de la alerta de página. El error es visible, conserva los datos y recibe el foco (cuarto Quality Gate, 968d912).

Corrección implementada (REV-14); pendiente de verificación visual en navegador.
