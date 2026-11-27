# REV-2026-11-27-gestionar-atencion-odontologica-desde-citas-01: Odontograma desde atención con paciente archivado responde el código y mensaje equivocados (draft_exists)

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-27-gestionar-atencion-odontologica-desde-citas.md (v1)
**Spec reference:** INV-04/INV-06, API-05, Edge cases (paciente archivado o cliente inactivo)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`EncounterCommands.create_odontogram` traduce **todo** `EvaluationStateError` a `EncounterStateError(..., 'draft_exists')`. Pero `EvaluationCommands._lock_patient` también lanza `EvaluationStateError` cuando el perfil está archivado («Reactiva el perfil odontológico…») o el cliente está inactivo.

## Expected behavior
Un paciente archivado o un cliente inactivo debe responder 409 con un código propio (`patient_archived` / `customer_inactive`, ya usados en `start`) y un mensaje acorde.

## Actual behavior
Se responde 409 con `code: draft_exists`; el frontend (`byCode`) muestra «El paciente tiene un odontograma en borrador: confírmalo o descártalo desde su ficha» (clave `VAL_DRAFT_EXISTS`), que es falso en ese caso. Además `patient_archived`, `customer_inactive`, `invalid_transition` e `invalid_state` no tienen clave `DENTISTRY.ENCOUNTER.VAL_*` en es/en/pt, por lo que en en/pt el usuario ve el texto en español del servidor.

## Evidence
- `backend/modules/dentistry/application/evaluations.py:24-32` (`_lock_patient` lanza `EvaluationStateError` para archivado/inactivo).
- `backend/modules/dentistry/application/encounters.py:131-132` (`except EvaluationStateError as exc: raise EncounterStateError(str(exc), 'draft_exists')`).
- `frontend/panel_admin/src/assets/i18n/en.json:913` (`VAL_DRAFT_EXISTS`); claves `VAL_*` presentes en `DENTISTRY.ENCOUNTER`: CLINICAL_FLOW_REQUIRED, DRAFT_EXISTS, DRAFT_PENDING, ENCOUNTER_CANCELLED, ENCOUNTER_FINISHED, NOT_DENTAL, NOT_ELIGIBLE, ODONTOGRAM_EXISTS, TOO_EARLY (sin PATIENT_ARCHIVED, CUSTOMER_INACTIVE, INVALID_TRANSITION, INVALID_STATE).
- No existe prueba de este caso en `test_encounter_api.py` (solo `draft_exists` por borrador previo).
