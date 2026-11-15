# REV-2026-11-15-validar-cobros-unificados-accounting-01: AC-10 sin corrida en navegador

**Status:** Open
**Severity:** Medium
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-11-15-validar-cobros-unificados-accounting.md (v1)
**Spec reference:** AC-10
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
La verificación en interfaz de productos y odontología (incluido Ventas deshabilitado) no se ejecutó en navegador: el worktree no tenía dependencias del frontend ni datos de desarrollo.
## Expected behavior
Guía ejecutada con resultados anotados.
## Actual behavior
Guía escrita (`docs/tests/MANUAL-validar-cobros-unificados-accounting.md`) y declarada «sin ejecutar»; el comportamiento tiene cobertura de integración de backend.
## Evidence
Informe del Quality Gate (2026-11-15): «AC-10 no cumplido en navegador»; backend 1648 tests OK. Se acepta para el PR; AC-10 no debe darse por cumplido hasta que alguien ejecute la guía.
