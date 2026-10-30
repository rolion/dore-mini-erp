# REV-2026-10-30-integracion-recepciones-entradas-inventario-02: Cálculo de stock_entry en el serializer

**Status:** Open
**Severity:** Low
**Category:** ARCHITECTURE
**Related plan:** docs/plans/PLAN-2026-10-30-integracion-recepciones-entradas-inventario.md (v1)
**Spec reference:** API-01, AC-06; docs/architecture/ddd.md (serializers validan forma y tipos)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build (backend)

## Description
receipt_representation decide stock_entry (modo inventory y producto presente en movimientos) en backend/modules/purchases/api/receipt_serializers.py.

## Expected behavior
La regla (stock_entry solo con modo inventory, derivada del libro) viva en application (GetReceipt/ReceiptDetail) y el serializer solo formatee.

## Actual behavior
La regla de negocio se calcula en la capa api (entered, stock_entry_known). Funcionalmente correcta y cubierta por pruebas de API.

## Evidence
backend/modules/purchases/api/receipt_serializers.py (líneas añadidas: entered / stock_entry_known).
