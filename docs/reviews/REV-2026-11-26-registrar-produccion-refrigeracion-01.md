# REV-2026-11-26-registrar-produccion-refrigeracion-01: Mensaje 400 del filtro de estado desactualizado

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-26-registrar-produccion-refrigeracion.md
**Spec reference:** AC-09
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El filtro invalido de la lista responde con un texto que no menciona los estados nuevos.

## Expected
Mensaje que liste all, draft, in_preparation y refrigerating.

## Actual
Dice 'Usa all, draft o in_preparation.' aunque refrigerating es valido.

## Evidence
backend/modules/production/api/order_views.py:117

## Resolución
Mensaje corregido (`Usa all, draft, in_preparation o refrigerating.`) y prueba `test_list_filter_message_names_refrigerating`.
