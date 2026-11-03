# REV-2026-11-03-perfil-odontologico-pacientes-03: Filtros perdidos al abrir el modal desde un enlace directo

**Status:** Resolved
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-02-perfil-odontologico-pacientes.md (v1)
**Spec reference:** AC-07
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description

Filtros perdidos al abrir el modal desde un enlace directo en la revisión del refactor frontend.

## Expected behavior

El modal debía pasar a la ficha el contexto de búsqueda, estado y página.

## Actual behavior

`openCreate()` capturaba los filtros antes de hidratar los parámetros de la URL.

## Evidence

El bloque `tap` de `PatientListComponent` asigna búsqueda, estado y página antes de llamar a `openCreate()`. `git diff --check origin/main` terminó con código 0.
