# REV-2026-11-17-asientos-manuales-navegacion-contable-02: Casos de uso de lectura y prueba de listado del PLAN no creados; sin prueba de número de consultas

**Status:** Open
**Severity:** Low
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-11-17-asientos-manuales-navegacion-contable.md (v1)
**Spec reference:** PLAN Files affected / pasos 1-2; Non-functional (sin N+1)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build (backend)

## Description
El PLAN preveía application/journal_queries.py (ListJournalEntries/GetJournalEntry) y tests/test_journal_listing.py. No existen: las vistas llaman a DjangoJournalRepository.search/get directamente y mapean con serializadores. Tampoco hay assertNumQueries sobre la lista.

## Expected behavior
Implementar lo previsto en el PLAN o actualizar el PLAN (v2) documentando la desviación; añadir una prueba que fije el número de consultas de la lista.

## Actual behavior
Funcionalmente correcto: search() usa select_related('reversed_by_entry') y el total viene de la cabecera, sin N+1 por lectura de código. Es coherente con las vistas existentes (views.py ya importa repositorios), por eso es Low.

## Evidence
ls backend/modules/accounting/application: sin journal_queries.py; backend/modules/accounting/tests/: sin test_journal_listing.py; journal_views.py:67-71 usa el repositorio en la vista.
