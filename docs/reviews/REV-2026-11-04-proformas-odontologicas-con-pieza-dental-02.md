# REV-2026-11-04-proformas-odontologicas-con-pieza-dental-02: Huecos de cobertura de pruebas en AC-06 y AC-08

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-04-proformas-odontologicas-con-pieza-dental.md (v1)
**Spec reference:** AC-06, AC-08, Test Specification (Integration tests)
**Plan mode:** COMPLETO
**Suggested owner:** backend (delivery-build)

## Description
`test_proforma_api.py` no cubre todos los casos que el PLAN declara.

## Expected behavior
AC-08: módulos `dentistry`, `customers` o `services` deshabilitados -> 403 `module_disabled`. AC-06: archivado -> 409 también en "nueva versión". Test Specification: "conteo de filas ajenas sin cambios" y acceso clínico obligatorio.

## Actual behavior
- `test_disabled_modules_return_403` itera solo `('services', 'dentistry')`; `customers` no se prueba.
- No hay prueba de `new-version` con paciente archivado (el código sí llama `require_active`).
- No hay prueba de un usuario no admin (CompanyClinicalPermission -> 403) ni de que PUT/present/new-version sobre una proforma de otra empresa no modifique sus filas (solo GET/present devuelven 404).
- Ninguna prueba de API envía `dental_piece` no textual (ver REV-01).

## Evidence
Revisión de `backend/modules/dentistry/tests/test_proforma_api.py` (líneas de `test_disabled_modules_return_403` y `test_patient_must_exist_be_active_and_customer_active`). La suite completa pasa (1425 tests), así que no hay fallo; solo cobertura incompleta del comportamiento ya implementado.
