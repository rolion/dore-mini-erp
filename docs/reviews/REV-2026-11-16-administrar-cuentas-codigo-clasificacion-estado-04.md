# REV-2026-11-16-administrar-cuentas-codigo-clasificacion-estado-04: La prueba de carrera por código duplicado no ejerce la rama de IntegrityError

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-16-administrar-cuentas-codigo-clasificacion-estado.md (v3)
**Spec reference:** EDGE «Carrera al crear dos cuentas con el mismo código»
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`test_race_on_duplicate_code_is_a_400_not_a_500` crea dos cuentas con el mismo código en secuencia, así que pasa por la comprobación previa y no por `except IntegrityError` de `DjangoAccountRepository.save`.

## Expected behavior
Una prueba que fuerce la restricción única (por ejemplo, simulando que la comprobación previa no ve el duplicado) y compruebe el 400 por campo.

## Actual behavior
La rama de `IntegrityError` no tiene prueba directa; el código es correcto por lectura.

## Evidence
Informe del Quality Gate repetido, hallazgo 1. Hay un patrón de `mock` imitable en `tests/test_classifications.py:142`.
