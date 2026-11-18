# REV-2026-11-18-revertir-asiento-al-anular-gasto-02: código residual en test_voiding_api.py

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-18-revertir-asiento-al-anular-gasto.md (v1)
**Spec reference:** N/A
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`test_voiding_api.py` termina con `__all__ = ['CATEGORIES']` (para silenciar un import sin uso) y hace `from uuid import UUID` dentro de `category_id()`.

## Expected behavior
Imports usados y `import` de `UUID` al inicio del módulo, sin `__all__`.

## Actual behavior
Código residual cosmético, sin impacto funcional.

## Evidence
Informe del Quality Gate: hallazgo L-2, severidad Low.
