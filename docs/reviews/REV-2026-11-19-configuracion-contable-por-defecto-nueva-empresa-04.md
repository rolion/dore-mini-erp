# REV-2026-11-19-configuracion-contable-por-defecto-nueva-empresa-04: Acoplamiento implícito con DEFAULT_ENABLED_KEYS

**Status:** Resolved
**Severity:** Medium
**Category:** ARCHITECTURE
**Related plan:** docs/plans/PLAN-2026-11-19-configuracion-contable-por-defecto-nueva-empresa.md (v1)
**Spec reference:** N/A
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
Aplicar el snapshot marca la empresa como inicializada (CompanySettingsModel) y los módulos por defecto de la siembra perezosa quedan cubiertos solo mientras el snapshot incluya los módulos por defecto.

## Expected behavior
Registrar la restricción en la ADR.

## Actual behavior
Aplicar el snapshot marca la empresa como inicializada (CompanySettingsModel) y los módulos por defecto de la siembra perezosa quedan cubiertos solo mientras el snapshot incluya los módulos por defecto.

## Evidence
Quality Gate aislado (subagente), informe del 2026-11-19: veredicto PASS; tests 1681 OK, ruff/flake8 limpios, bandit sin Medium/High.
