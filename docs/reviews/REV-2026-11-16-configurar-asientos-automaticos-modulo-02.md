# REV-2026-11-16-configurar-asientos-automaticos-modulo-02: Pruebas incompletas para AC-08 (hueco) y AC-11 (403 de no administradores)

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-16-configurar-asientos-automaticos-modulo.md (v1)
**Spec reference:** AC-08, AC-11, tabla AC→verificación
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
La tabla AC→verificación del plan declara cubrir AC-08 «deshabilitar y volver a habilitar» y AC-11 «403/401», pero las pruebas no lo comprueban.

## Expected behavior
AC-08: prueba en test_posting_service que deshabilite/habilite Contabilidad y compruebe reason=in_gap sin asiento. AC-11: un usuario no administrador recibe 403 y sin sesión 401.

## Actual behavior
test_posting_service solo cubre accounting_disabled y before_cutoff (el hueco in_gap solo se prueba en test_coverage.py sobre coverage_status, no a través de post_automatic_entry/check_posting_ready). test_posting_config_api.test_company_isolation_and_access solo prueba sin sesión y con assertIn(status, (401, 403)); no hay caso con un usuario no administrador ni exige 401 exacto.

## Evidence
grep in_gap backend/modules/accounting -> solo domain/coverage.py, services.py y tests/test_coverage.py (ninguna referencia en test_posting_service.py). Suite backend completa: Ran 1959 tests ... OK (las pruebas existentes pasan; el hueco es de cobertura de pruebas, no un fallo).

## Resolution
Pruebas añadidas: hueco de cobertura (`in_gap`) por la fachada y usuario sin empresa → 403 en las tres rutas, anónimo → 401 exacto.
