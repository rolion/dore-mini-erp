# REV-2026-11-26-numeracion-correlativa-compras-03: Huecos de cobertura frente a la Test Specification (descripciones de asiento, API-03, EDGE-02, desempate de la migración)

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-26-numeracion-correlativa-compras.md (v1)
**Spec reference:** AC-11, API-03, EDGE-02, AC-12 (orden `confirmed_at, created_at, id`)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build (backend tests)

## Description
La tabla «Acceptance criteria mapping» promete para AC-11 «API (lista/detalle/recepción/búsqueda), integración (descripciones de asiento)» y la Test Specification menciona la serie con Contabilidad deshabilitada. Varias de esas verificaciones solo existen de forma indirecta.

## Expected behavior
- Un test de integración que registre una recepción, un pago/anticipo y una reversión sobre una compra numerada y compruebe que la descripción del asiento contiene `NC-…` y ` (período)`.
- Un test de API que compruebe `purchase.reference == 'NC-…'` en el detalle/lista de recepciones (API-03).
- EDGE-02: confirmar con Contabilidad deshabilitada y sin períodos responde 409 `fiscal_period_missing`.
- AC-12: la migración 0011 con empates de `confirmed_at` ordena por `created_at` y luego `id`.

## Actual behavior
- Descripciones: solo `test_the_accounting_text_carries_the_period` llama a `_period_suffix` (función privada) directamente; `test_purchase_posting.py:270` comprueba `assertIn(purchase['reference'], entry.description)` (ahora `NC-…`) pero no el período, y no hay aserción sobre las descripciones de pago/anticipo ni de reversión.
- API-03: ningún test de recepciones asegura el valor `NC-…` de `purchase.reference` (solo el patrón `REC-…` de la recepción). Se confía en que el serializer reutiliza `purchase.reference`.
- EDGE-02: sin test; el comportamiento se deduce de que `lock_open_period` no depende del módulo (lectura de código).
- Migración: el test siembra `confirmed_at` distintos; no ejercita el desempate `created_at, id` (el parámetro `created_minutes` de `make` existe pero no se usa con empates).
No hay defecto funcional detectado en esos puntos; son verificaciones prometidas por el plan sin test que las proteja.

## Evidence
`grep -rn "NC-0" backend/modules --include=*.py` solo encuentra `domain/purchase.py`, `purchase_repository.py`, `test_purchase_numbering.py` y `test_purchase_number_domain.py`: ningún test de recepciones, pagos o asientos.
`grep -n "description\|Compra COM" test_purchase_posting.py test_payment_posting.py test_receipt_revert.py` → solo `test_purchase_posting.py:270-271`.

## Resolución
Resuelto: `AccountingTextTests` (descripciones de reconocimiento, pago/anticipo y reversión con `NC-…` y período), aserción `(Año)` en el asiento de recepción real, `NC-…` en la recepción (API-03), `test_confirm_with_no_periods_at_all_is_a_409` (EDGE-02) y `test_same_confirmation_time_is_broken_by_creation_time` (desempate de la migración).
