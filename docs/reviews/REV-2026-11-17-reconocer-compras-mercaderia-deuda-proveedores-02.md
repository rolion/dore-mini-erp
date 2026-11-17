# REV-2026-11-17-reconocer-compras-mercaderia-deuda-proveedores-02: Revertir una recepción con Contabilidad deshabilitada hoy deja el asiento sin revertir

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-17-reconocer-compras-mercaderia-deuda-proveedores.md (v1)
**Spec reference:** AC-07 (revertir una recepción con asiento crea el asiento de reversión), Expected behavior (Revertir)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`PurchasePostingAdapter.reverse_receipt` retorna sin hacer nada si `is_available()` es falso (módulo Contabilidad deshabilitado hoy). Una recepción contabilizada cuando Contabilidad estaba habilitada y revertida después de deshabilitarlo queda revertida (stock, estado) pero su asiento sigue publicado, sin reversión.

## Expected behavior
Un asiento existente de la recepción se revierte con la recepción, o la decisión de no hacerlo está documentada (ADR/Specification) como aceptada.

## Actual behavior
Recepción revertida; el saldo de Inventario/Proveedores conserva el asiento original. La Specification solo define el caso «sin asiento» y «período cerrado»; el caso «módulo deshabilitado con asiento previo» no está en edge cases ni probado.

## Evidence
```
backend/modules/purchases/infrastructure/adapters.py  PurchasePostingAdapter.reverse_receipt:
    if not self.is_available():
        return
```
Sin prueba que cubra deshabilitar Contabilidad entre recibir y revertir (la prueba existente cubre el caso inverso: recibir sin Contabilidad y revertir con ella).
