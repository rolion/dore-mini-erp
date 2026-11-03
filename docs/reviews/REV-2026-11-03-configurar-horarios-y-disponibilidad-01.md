# REV-2026-11-03-configurar-horarios-y-disponibilidad-01: Falla el límite de arquitectura de Agenda

**Status:** Open
**Severity:** High
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-03-configurar-horarios-y-disponibilidad.md (v1)
**Spec reference:** AC-01
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Evidence

La prueba de límites rechaza `modules\agenda\infrastructure\personnel.py importa modules.personnel.services`. La corrida encontró 11 pruebas y terminó `FAILED (failures=1)`.
