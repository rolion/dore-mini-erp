# REV-2026-11-27-crm-tableros-seguimiento-comercial-01: la prueba de claves de la respuesta no incluye `description`

**Status:** Resolved
**Severity:** High
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-27-crm-tableros-seguimiento-comercial.md (v1)
**Spec reference:** AC-07 / API-01
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`CreateTests.test_create_for_lead_in_first_stage_with_initial_history` compara el conjunto exacto de claves de la respuesta; la respuesta ahora incluye `description`.
## Expected behavior
La prueba existente se actualiza con el contrato aditivo.
## Actual behavior
`test_api_opportunities.py:91-93` no listaba `description`; fallaría al ejecutarse con BD.
## Evidence
Revisión por lectura del Quality Gate (no ejecutable sin PostgreSQL). Corregido añadiendo `'description'` al conjunto.
