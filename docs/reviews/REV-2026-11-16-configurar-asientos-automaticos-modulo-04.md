# REV-2026-11-16-configurar-asientos-automaticos-modulo-04: Estilo: líneas > 120 caracteres y assert de invariante del catálogo en código nuevo

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-16-configurar-asientos-automaticos-modulo.md (v1)
**Spec reference:** Calidad de código (flake8/bandit)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
flake8 --max-line-length=120 y bandit sobre los archivos nuevos/modificados de accounting.

## Expected behavior
Sin avisos nuevos de flake8; invariantes del catálogo sin depender de assert (se eliminan con python -O).

## Actual behavior
flake8 reporta E501 en código nuevo: application/use_cases.py:261 (comentario de ConfigureMethod, 128 car.), services.py:63, 66 y 68 (el __all__ ampliado). bandit: B101 assert_used (Severity Low) en domain/posting.py:62 (Event.__post_init__ valida código ≤ 30, debit_role y credit_role con assert). Los E501 de use_cases.py:135/245, repositories.py:383/421 y services.py:155 son preexistentes.

## Evidence
flake8: modules/accounting/application/use_cases.py:261:121 E501 (128 > 120); modules/accounting/services.py:63:121, 66:121, 68:121 E501.
bandit: Issue B101 Severity: Low Confidence: High, Location modules/accounting/domain/posting.py:62:8. Sin issues Medium/High.

## Resolution
E501 corregidos en código nuevo y `Event.__post_init__` valida con `ValueError` en lugar de `assert`.
