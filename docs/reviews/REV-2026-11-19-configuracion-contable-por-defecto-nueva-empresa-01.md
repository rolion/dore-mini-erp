# REV-2026-11-19-configuracion-contable-por-defecto-nueva-empresa-01: Desviaciones sin declarar y ADR en Propuesto

**Status:** Open (no bloquea el PASS)
**Severity:** Low
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-11-19-configuracion-contable-por-defecto-nueva-empresa.md (v1)
**Spec reference:** N/A
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El plan y la ADR citan `shared/company_defaults.py` pero se implementó como paquete (aloja snapshot.json); la ADR sigue «Propuesto» y `docs/producto/modulos-implementados.md` no se actualizó.

## Expected behavior
Desviación declarada en ## Implementación y ADR aceptada.

## Actual behavior
El plan y la ADR citan `shared/company_defaults.py` pero se implementó como paquete (aloja snapshot.json); la ADR sigue «Propuesto» y `docs/producto/modulos-implementados.md` no se actualizó.

## Evidence
Quality Gate aislado (subagente), informe del 2026-11-19: veredicto PASS; tests 1681 OK, ruff/flake8 limpios, bandit sin Medium/High.
