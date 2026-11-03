# REV-2026-11-03-configurar-horarios-y-disponibilidad-04: La semana vacía puede quedar sin mensaje

**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-03-configurar-horarios-y-disponibilidad.md (v1)
**Spec reference:** AC-04
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Evidence

`WeekView` serializa turnos con vigencia intersectada aunque su día no ocurra en esa vigencia. La vista oculta el mensaje de vacío al encontrar uno de esos turnos.
