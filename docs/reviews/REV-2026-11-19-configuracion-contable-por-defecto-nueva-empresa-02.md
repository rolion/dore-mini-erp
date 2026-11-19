# REV-2026-11-19-configuracion-contable-por-defecto-nueva-empresa-02: Falta cobertura de dry-run con cobertura/corte e INV-01 directo

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-19-configuracion-contable-por-defecto-nueva-empresa.md (v1)
**Spec reference:** INV-01, AC-07
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
No hay test de que el dry-run revierta cobertura y corte, ni de que aplicar a una empresa no toque a otra, ni un boundary test que impida a shared/company_defaults importar modules.*.

## Expected behavior
Un test por cada punto.

## Actual behavior
No hay test de que el dry-run revierta cobertura y corte, ni de que aplicar a una empresa no toque a otra, ni un boundary test que impida a shared/company_defaults importar modules.*.

## Evidence
Quality Gate aislado (subagente), informe del 2026-11-19: veredicto PASS; tests 1681 OK, ruff/flake8 limpios, bandit sin Medium/High.
