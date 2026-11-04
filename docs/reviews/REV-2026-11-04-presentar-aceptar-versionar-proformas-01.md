# REV-2026-11-04-presentar-aceptar-versionar-proformas-01: Pruebas de API con PostgreSQL sin ejecutar

**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-04-presentar-aceptar-versionar-proformas.md (v1)
**Spec reference:** AC-02, AC-03, AC-06, AC-08..13, AC-15
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Las pruebas de integración `quotations/tests/test_decisions_api.py` y `dentistry/tests/test_proforma_decisions_api.py`, la regresión de `test_api.py`/`test_proforma_api.py`, `modularity` y la suite completa necesitan PostgreSQL. En este entorno no hay `DATABASE_URL` ni credenciales (no se lee `.env`), así que no se ejecutaron.

## Expected behavior
Todas pasan contra PostgreSQL.

## Actual behavior
No ejecutadas: ningún AC de API está verificado con evidencia real.

## Evidence
`DATABASE_URL` sin definir (proceso, usuario y máquina); con una URL ficticia PostgreSQL responde `password authentication failed for user "u"`.
Ejecutado sin base de datos: dominio de ambos módulos y `test_boundaries` → `Ran 46 tests ... OK`; `makemigrations --check` → `No changes detected`.
Comando pendiente (desde `backend/`, con `DJANGO_SETTINGS_MODULE=config.settings.test` y `DATABASE_URL` válida): `python manage.py test modules.quotations modules.dentistry modules.modularity modules.service_catalog modules.sales.tests.test_boundaries`
