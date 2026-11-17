# REV-2026-11-17-reconocer-compras-mercaderia-deuda-proveedores-07: Higiene de lint en Python nuevo (líneas >120, imports sin uso, nombre `l`)

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-17-reconocer-compras-mercaderia-deuda-proveedores.md (v2)
**Spec reference:** Revisión técnica (líneas >120 caracteres en Python nuevo; CLAUDE.md)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El proyecto no define configuración de lint Python; con `ruff --line-length 120 --select E,F,W` sobre los archivos .py cambiados hay hallazgos introducidos por v2: líneas de 121+ caracteres añadidas (accounting/services.py ×2 —docstrings—, accounting/tests/test_posting_config_api.py 127, test_posting_domain.py 121, purchases/tests/test_payment_api.py 135, test_payment_classification_api.py 122, test_payment_posting.py 121), imports sin uso (purchases/tests/test_payment_classification_api.py: DEFAULT_ENABLED_KEYS, set_enabled; test_purchase_posting.py: ConfigureMethod, DjangoAccountRepository, DjangoMethodMappingRepository, money_account; `ReceiptAlreadyReverted` en receipt_commands.py puede ser anterior) y variable `l` ambigua (test_payment_posting.py:249, test_purchase_posting_unit.py:149).

## Expected behavior
Sin líneas >120 ni imports sin uso en lo nuevo.

## Actual behavior
Sin impacto funcional.

## Evidence
```
$ ruff check --line-length 120 --select E,F,W <archivos .py del diff> --output-format concise
Found 22 errors.   (E501, F401, E741; algunas preexistentes)
$ git diff origin/accounting...HEAD -U0 -- '*.py' | awk (líneas añadidas >120)
accounting/services.py: 121 (x2); accounting/tests/test_posting_config_api.py: 127; test_posting_domain.py: 121;
purchases/tests/test_payment_api.py: 135; test_payment_classification_api.py: 122; test_payment_posting.py: 121
```
