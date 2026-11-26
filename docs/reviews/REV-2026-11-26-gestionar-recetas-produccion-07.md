# REV-2026-11-26-gestionar-recetas-produccion-07: Descripción del módulo menciona órdenes fuera de alcance

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-26-gestionar-recetas-produccion.md (v1)
**Spec reference:** AC-10
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
La descripción en `MODULE_CATALOG` dice «Recetas y órdenes de producción», pero las órdenes no existen aún.

## Expected behavior
Descripción acorde al alcance.

## Actual behavior
Texto visible en la pantalla de módulos.

## Evidence
`modularity/domain/modules.py` (ModuleDefinition production).
