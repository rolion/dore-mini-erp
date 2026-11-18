# REV-2026-11-16-configurar-seis-clasificaciones-contables-02: AC-06 sin prueba con rol no administrador

**Status:** Open
**Severity:** Low
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-11-16-configurar-seis-clasificaciones-contables.md (v1)
**Spec reference:** AC-06
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
AC-06 pide 403 para quien no administra la empresa. Las pruebas cubren anónimo, usuario sin empresa y aislamiento entre empresas.

## Expected behavior
Una prueba con usuario no administrador de una empresa.

## Actual behavior
La vista usa el mismo gate que el resto de la configuración y no existe un rol intermedio verificado; el caso no está probado.

## Evidence
`tests/test_account_classes.py::test_requires_authentication_and_company`. Informe del Quality Gate, hallazgo Low-2.
