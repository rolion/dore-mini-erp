# REV-2026-11-16-periodos-fiscales-por-empresa-04: Faltan pruebas unitarias de casos de uso

**Status:** Open (no bloqueante)
**Severity:** Low
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-11-16-periodos-fiscales-por-empresa.md (v1)
**Spec reference:** AC-03, AC-08
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Solapamiento y puerto de uso solo se cubren vía API y concurrencia; el PLAN prometía unitarias con puerto simulado.

## Expected behavior
Añadir tests de casos de uso o ajustar el mapa del PLAN.

## Actual behavior
Ver descripción.

## Evidence
Quality Gate (subagente aislado), PLAN Test Specification › Unit tests. Backend 1678 OK; frontend 1430 OK (2 de 3 corridas, ver nota del flake preexistente `screens-i18n.spec.ts:58-65`, ajeno al diff).
