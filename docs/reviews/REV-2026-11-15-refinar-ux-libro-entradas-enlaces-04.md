# REV-2026-11-15-refinar-ux-libro-entradas-enlaces-04: Prueba del aviso tenue incompleta

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-15-refinar-ux-libro-entradas-enlaces.md (v1)
**Spec reference:** AC-04
**Plan mode:** COMPACTO
**Suggested owner:** delivery-build

## Description
Prueba del aviso tenue incompleta.

## Expected behavior
La prueba afirma bg-info-subtle, text-info-emphasis y border-info-subtle.

## Actual behavior
Solo afirma bg-info-subtle.

## Evidence
entry-list.component.spec.ts: `expect(byId('context-note')?.classList).toContain('bg-info-subtle')`.

## Resolution
Corregido: la prueba afirma las tres clases del aviso tenue.
