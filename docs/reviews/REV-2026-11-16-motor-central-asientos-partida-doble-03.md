# REV-2026-11-16-motor-central-asientos-partida-doble-03: Lint menor en código nuevo (E741 y F401)

**Status:** Resolved (verificado en el segundo Quality Gate)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-16-motor-central-asientos-partida-doble.md (v1)
**Spec reference:** CLAUDE.md (calidad); sin AC asociado
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Código nuevo sin avisos de flake8 evitables.

## Expected behavior
Sin variables ambiguas ni imports sin usar en archivos añadidos.

## Actual behavior
`services.py:376` usa la variable `l`; `test_journal_domain.py:93-94` y `test_journal_service.py:44` también; `test_journal_concurrency.py:4` importa `date` sin usarlo.

## Evidence
`python -m flake8 --max-line-length 140 modules/accounting` -> E741 en services.py:376, test_journal_domain.py:93/94, test_journal_service.py:44; F401 en test_journal_concurrency.py:4. (ruff reporta 165 en todo el paquete, mayormente preexistentes.)
