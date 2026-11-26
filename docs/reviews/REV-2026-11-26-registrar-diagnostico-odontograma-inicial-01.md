# REV-2026-11-26-registrar-diagnostico-odontograma-inicial-01: Cliente inactivo provoca 500 en crear/editar/confirmar/enmendar evaluaciones

**Status:** Closed
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-26-registrar-diagnostico-odontograma-inicial.md (v1)
**Spec reference:** INV-12 («Paciente archivado o cliente inactivo: sin crear/editar/confirmar/enmendar; lectura permitida»), AC-09
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`PatientGate.require_active` (`backend/modules/dentistry/infrastructure/adapters.py`, ya existente de PB-ODO-001) lanza `DentalProformaValidationError` cuando el cliente del paciente está inactivo. `EvaluationCommands._lock_patient` (`backend/modules/dentistry/application/evaluations.py:23-26`) lo llama y la función `run()` de `backend/modules/dentistry/api/evaluation_views.py:45-53` solo traduce `EvaluationNotFound/PatientNotFound`, `EvaluationValidationError`, `EvaluationStateError/PatientArchived`. La excepción de proformas no se captura.

## Expected behavior
Cliente inactivo → respuesta 4xx controlada (400 o 409, coherente con el archivado), sin crear/editar/confirmar/enmendar.

## Actual behavior
HTTP 500 (error de servidor, página HTML) al hacer `POST /api/dentistry/patients/<id>/evaluations/`; lo mismo ocurre en PUT/DELETE/confirm/amend porque todos pasan por `_lock_patient`. No hay prueba para este caso (`test_odontogram_api.py` solo cubre perfil archivado).

## Evidence
Prueba temporal (borrada tras ejecutarse; el worktree quedó limpio) con `CustomerModel.objects.filter(id=...).update(active=False)` y luego `POST` de una evaluación válida:

```
INACTIVE CUSTOMER POST -> 500 b'\n<!doctype html>\n<html lang="en">\n<head>\n  <title>Server Error (500)</title>...
```


## Verificación Quality Gate #2
Cerrado. `_lock_patient` traduce `DentalProformaValidationError` a `EvaluationStateError` (409). Prueba `test_inactive_customer_blocks_changes_with_409` cubre POST/PUT/confirm/DELETE/amend; suite completa: Ran 2597 tests, OK.
