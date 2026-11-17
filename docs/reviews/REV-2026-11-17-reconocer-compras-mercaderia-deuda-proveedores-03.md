# REV-2026-11-17-reconocer-compras-mercaderia-deuda-proveedores-03: Pruebas de la Test Specification no escritas y no declaradas como desviación

**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-17-reconocer-compras-mercaderia-deuda-proveedores.md (v1)
**Spec reference:** Test Specification (Unit tests, Integration tests) y mapeo AC→verificación
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
La Test Specification exige: unit de dominio de `Purchase.receipt_amount` (parcial, completa, redondeo, cero), unit de aplicación con puerto falso (publica una vez, no publica en reintento, propaga rechazo sin guardar, revierte asiento antes de marcar revertida), unit del serializer (AC-08) y cobertura por hueco. La ## Implementación solo declara como desviación la prueba de concurrencia con hilos. Existe únicamente `purchases/tests/test_purchase_posting.py` (integración, 17 pruebas).

## Expected behavior
Cada rama nueva con prueba o desviación declarada.

## Actual behavior
Sin prueba: (a) dominio `receipt_amount` aislado; (b) comandos con puerto falso; (c) `RevertStockShortage` NO revierte el asiento (edge case de la Specification); (d) `ledger_rejected` / `ledger_conflict`; (e) cobertura por hueco (`in_gap`); (f) reversión parcial/re-recepción (ver REV-01). Aclaración: las ramas (c)-(e) son correctas por lectura del código (todo corre en la `transaction.atomic` de `_run`; el stock se revierte antes que el asiento).

## Evidence
```
grep "def test_" backend/modules/purchases/tests/test_purchase_posting.py -> 17 pruebas, todas de integración
ls backend/modules/purchases/tests | grep -i posting -> solo test_purchase_posting.py
```
