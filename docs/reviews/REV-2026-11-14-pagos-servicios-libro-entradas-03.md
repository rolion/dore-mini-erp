# REV-2026-11-14-pagos-servicios-libro-entradas-03: Imports sin ordenar en collections.py

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-14-pagos-servicios-libro-entradas.md (v1)
**Spec reference:** N/A
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`from typing import Protocol` queda entre `collections.abc` y `dataclasses`.

## Expected behavior
Imports ordenados.

## Actual behavior
Orden no alfabético (cosmético).

## Evidence
`backend/modules/receivables/application/collections.py` líneas 1-5.

## Resolución
Imports de `collections.py` reordenados.
