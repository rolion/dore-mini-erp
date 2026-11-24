# REV-2026-11-24-cancelar-ventas-registrar-devoluciones-02: Tres avisos E501 nuevos en líneas cambiadas (la tarea declaró cero)

**Status:** Resolved (corregido en delivery-build, 2026-11-24)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-24-cancelar-ventas-registrar-devoluciones.md (v1)
**Spec reference:** CLAUDE.md (lint: cero avisos en lo cambiado)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`ruff check` y `flake8` sobre los 23 `.py` cambiados (sin migraciones) reportan líneas de más de 120 caracteres introducidas por la tarea. `docs/tasks/...md` afirma «sin avisos nuevos en lo cambiado».

## Expected behavior
Cero avisos nuevos en las líneas cambiadas.

## Actual behavior
Avisos E501 en líneas añadidas/modificadas (cruzado con `git diff -U0`): `backend/modules/costing/services.py:11` (132), `backend/modules/sales/application/commands.py:248` (121, docstring de `CancelOrder`), `backend/modules/sales/application/ports.py:204` (121, docstring de `reverse_delivery`). El resto de avisos (views.py, order.py:445, test_api.py:214/646, E301 de views.py, etc.) son previos.

## Evidence
```
$ ruff check <23 archivos>  -> Found 8 errors (3 en líneas nuevas)
modules\costing\services.py:11:121: E501 Line too long (132 > 120)
modules\sales\application\commands.py:248:121: E501 Line too long (121 > 120)
modules\sales\application\ports.py:204:121: E501 Line too long (121 > 120)
$ flake8 <23 archivos> -> mismos 3 E501 en líneas cambiadas (más deuda previa)
```
