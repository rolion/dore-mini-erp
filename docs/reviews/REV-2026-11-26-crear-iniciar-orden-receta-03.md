# REV-2026-11-26-crear-iniciar-orden-receta-03: nota de Producción en ddd.md desactualizada y con referencia duplicada

**Status:** Resolved
**Severity:** Low
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-11-26-crear-iniciar-orden-receta.md (v1)
**Spec reference:** Files/components affected (Docs: `docs/architecture/ddd.md`)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
La nota «Producción › Recetas, DORE-PROD-001» agrega la frase de órdenes al final, pero conserva «requiere Catálogo» y «Hoy solo contiene el agregado `Recipe`», que ahora son falsos (el módulo requiere Catálogo e Inventario y contiene también `ProductionOrder`). Además termina con dos «Ver ADR…» seguidos.

## Expected behavior
Nota coherente: módulo requiere `catalog` e `inventory`, contiene `Recipe` y `ProductionOrder`, una sola lista de ADR.

## Actual behavior
Texto contradictorio dentro del mismo párrafo.

## Evidence
`git diff origin/produccion...HEAD -- docs/architecture/ddd.md` (línea de la nota DORE-PROD-001).
