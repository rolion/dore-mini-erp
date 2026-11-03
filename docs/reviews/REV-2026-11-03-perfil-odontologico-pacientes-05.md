# REV-2026-11-03-perfil-odontologico-pacientes-05: Botón de cierre sin título

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-02-perfil-odontologico-pacientes.md (v1)
**Spec reference:** AC-08 / sistema de diseño §7
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description

Botón de cierre sin título en la revisión del refactor frontend.

## Expected behavior

El botón de solo icono debía tener `aria-label` y `title`.

## Actual behavior

El cierre del modal solo declaraba `aria-label`.

## Evidence

El botón ahora declara `aria-label="Cerrar"` y `title="Cerrar"`. `All files pass linting.`
