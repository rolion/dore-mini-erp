# REV-2026-11-15-incorporar-egresos-reversion-libro-05: `count` de totales incluye reversiones y `amount` no; sin documentar en la API

**Status:** Open (no bloqueante)
**Severity:** Low
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-11-15-incorporar-egresos-reversion-libro.md (v1)
**Spec reference:** API-02
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
`count` suma todas las filas del filtro (con reversiones); `amount`/`by_origin` son solo ingresos originales. Es compatible hacia atrás pero no está dicho en la Specification.

## Expected behavior
Aclararlo en API-02.

## Actual behavior
Ver descripción.

## Evidence
`DjangoEntryRepository.totals` en `repositories.py`.
