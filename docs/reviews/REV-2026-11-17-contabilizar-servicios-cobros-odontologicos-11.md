# REV-2026-11-17-contabilizar-servicios-cobros-odontologicos-11: Línea de 122 caracteres en `test_api.py:76`

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-17-contabilizar-servicios-cobros-odontologicos.md (v1)
**Spec reference:** —
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Solo en una prueba; el código de producción nuevo cumple 120.

## Expected behavior
Cobertura de pruebas y documentación coherentes con la Specification y el sistema de diseño.

## Actual behavior
Ver descripción.

## Evidence
Quality Gate, 2.ª pasada (subagente aislado, HEAD b778d3d). Cosmético.

Resuelto: la línea se partió; además `ruff` y `flake8` quedan en el proyecto (`backend/ruff.toml`, `backend/.flake8`, `requirements/dev.txt`) y pasan sobre todos los `.py` del diff.
