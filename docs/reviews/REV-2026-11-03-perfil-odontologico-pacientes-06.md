# REV-2026-11-03-perfil-odontologico-pacientes-06: Contraste insuficiente de etiquetas de estado

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-02-perfil-odontologico-pacientes.md (v1)
**Spec reference:** AC-08 / sistema de diseño §7
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description

Contraste insuficiente de etiquetas de estado en la revisión del refactor frontend.

## Expected behavior

Las etiquetas de estado debían alcanzar un contraste mínimo de 4,5:1.

## Actual behavior

Con la paleta clara de Bootstrap los pares iniciales daban 3,49:1 (activo) y 3,65:1 (archivado e historial).

## Evidence

Las etiquetas ahora usan `text-success-emphasis`, `text-secondary-emphasis` y `text-warning-emphasis` con sus fondos sutiles. Con la paleta clara de Bootstrap los pares corregidos de activo y archivado dan 10,35:1 y 10,51:1. `All files pass linting.`
