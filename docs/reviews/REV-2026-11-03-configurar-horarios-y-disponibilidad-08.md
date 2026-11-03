# El error se comparte entre página y diálogos

**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-03-configurar-horarios-y-disponibilidad.md (v1)
**Spec reference:** AC-04
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Evidence

Un único `error` se muestra en la página y en ambos diálogos. Tras fallar Guardar turno, "Registrar ausencia" muestra el error del turno.

Origen: tercer Quality Gate independiente sobre `7d521eb`.
