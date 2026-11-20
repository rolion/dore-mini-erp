# REV-2026-11-19-configuracion-contable-por-defecto-nueva-empresa-03: DefaultsError en el alta responde 500

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-19-configuracion-contable-por-defecto-nueva-empresa.md (v1)
**Spec reference:** AC-09
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Si el snapshot es inválido, DefaultsError sube sin capturar y la API responde 500 (la empresa sí se revierte).

## Expected behavior
Decisión declarada: el snapshot lo versiona el repo, por lo que es un error de despliegue.

## Actual behavior
Si el snapshot es inválido, DefaultsError sube sin capturar y la API responde 500 (la empresa sí se revierte).

## Evidence
Quality Gate aislado (subagente), informe del 2026-11-19: veredicto PASS; tests 1681 OK, ruff/flake8 limpios, bandit sin Medium/High.
