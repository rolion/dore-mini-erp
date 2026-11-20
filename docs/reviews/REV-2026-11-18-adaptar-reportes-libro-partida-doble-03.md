# REV-2026-11-18-adaptar-reportes-libro-partida-doble-03: Avisos E501 nuevos y clave i18n sin uso

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-18-adaptar-reportes-libro-partida-doble.md (v1)
**Spec reference:** Lint (CLAUDE.md: cero avisos en lo cambiado); i18n
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Se exige cero avisos de lint en lo cambiado; hay líneas largas nuevas. Además se añadió una clave de traducción sin usar.

## Expected behavior
Cero avisos nuevos de ruff/flake8; sin claves i18n huérfanas.

## Actual behavior
Dos E501 nuevos (el resto de los 6 avisos son preexistentes en líneas no tocadas): repositories.py:603 (docstring de money_lines, 122 > 120) y reporting/application/criteria.py:6 (123 > 120). La clave `REPORTING.REPORTS.OPERATIVO` se agregó en es/en/pt pero la plantilla usa solo `CRITERIO_OPERATIVO`.

## Evidence
- ruff/flake8: modules/accounting/infrastructure/django/repositories.py:603:121 E501; modules/reporting/application/criteria.py:6:121 E501
- git show 099f3d5 -- frontend/panel_admin/src/assets/i18n/es.json (clave OPERATIVO); grep en reports.component.html: sin uso

## Resolución
Corregido: línea de `criteria.py` acortada y clave i18n `OPERATIVO` sin uso eliminada (el E501 de `repositories.py:603` ya no existe).

Verificado en la segunda pasada del Quality Gate (PASS).
