# REV-2026-11-15-cuentas-dinero-clasificaciones-02: EDGE-02 y edición de cuenta legada en UI sin prueba directa

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-15-cuentas-dinero-clasificaciones.md (v1)
**Spec reference:** EDGE-02, AC-05 (UI)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
1) EDGE-02 (duplicado concurrente -> `IntegrityError` -> 400): `DjangoClassificationRepository.save` tiene la rama `except IntegrityError`, pero `test_classifications.py` solo prueba el duplicado secuencial (pre-chequeo `iexact`). 2) `account-dialog` exige `kind` (Validators.required) también al editar una cuenta legada sin tipo (conforme al ADR: «se piden completar al editarlas»), pero ningún spec cubre abrir una cuenta con `kind: null`.

## Expected behavior
Una prueba que simule la carrera (p. ej. mock de `update_or_create` con `IntegrityError`) y un spec de edición de cuenta legada con `kind: null`.

## Actual behavior
Ramas implementadas pero sin test directo. Comportamiento observado en código correcto; sin defecto funcional detectado.

## Evidence
`grep IntegrityError backend/modules/accounting/tests/test_classifications.py` -> sin coincidencias. `account-dialog.component.spec.ts` solo usa `kind: 'BANK'` al editar (línea 82) y no hay caso `kind: null`.
