# REV-2026-11-03-perfil-odontologico-pacientes-01: Cambios de historial ocultos por etiquetas coincidentes

**Status:** Resolved
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-02-perfil-odontologico-pacientes.md (v1)
**Spec reference:** AC-05
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description

Cambios de historial ocultos por etiquetas coincidentes en la revisión del refactor frontend.

## Expected behavior

El historial debía mostrar cada cambio efectivo con valores anterior y nuevo.

## Actual behavior

La comparación de textos formateados omitía el cambio entre un valor ausente y el texto literal «No informado».

## Evidence

`PatientHistoryComponent.changes` ahora compara `(row.before[key] ?? '') !== (row.after[key] ?? '')` antes de formatear. El caso tiene prueba de regresión. `TOTAL: 1084 SUCCESS`.
