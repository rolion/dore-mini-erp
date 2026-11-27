# REV-2026-11-26-reporte-balance-general-contabilidad-02: API-01 del plan no coincide con el contrato implementado

**Status:** Fixed
**Severity:** Medium
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-11-26-reporte-balance-general-contabilidad.md (v1)
**Spec reference:** API-01
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
El ejemplo JSON del plan mostraba `total` como cadena; el serializer, el DTO TS y el fixture usan objetos `{opening, movement, closing}`.

## Expected behavior
El plan describe el contrato real.

## Actual behavior
Texto desfasado, sin desviación documentada.

## Evidence
`api/balance_sheet_serializers.py` (`_amounts`) vs. PLAN v1, API-01.

## Resolución
PLAN v2 (solo Implementation Plan / ejemplo de contrato; sin cambio de comportamiento ni de AC), con changelog.
