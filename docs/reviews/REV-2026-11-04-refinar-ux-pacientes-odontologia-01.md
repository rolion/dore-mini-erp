# REV-2026-11-04-refinar-ux-pacientes-odontologia-01: Edad con plural incorrecto («1 años», «0 años»)

**Status:** Resolved (corregido en el commit siguiente al Quality Gate; verificado con pruebas propias, pendiente de re-revisión independiente)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-04-refinar-ux-pacientes-odontologia.md (v1)
**Spec reference:** AC-22 (edad junto a la fecha), AC-12 (badge «Menor · N años»), AC-08
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Las claves DENTISTRY.PATIENT_DETAIL.EDAD_ANOS y MENOR_EDAD_ANOS usan un texto fijo con «años»; no hay forma plural.

## Expected behavior
Para edad 1 se lee «1 año» (y su equivalente en en/pt: «1 year», «1 ano»); para 0, «0 años» o «menos de 1 año».

## Actual behavior
Con edad 1 la ficha muestra «12/03/2025 · 1 años» y el badge «Menor · 1 años»; en inglés «1 years».

## Evidence
es.json: "EDAD_ANOS": "{{n}} años", "MENOR_EDAD_ANOS": "Menor · {{n}} años" (frontend/panel_admin/src/assets/i18n/{es,en,pt}.json). Uso: patient-detail.component.html:18 y :162.
