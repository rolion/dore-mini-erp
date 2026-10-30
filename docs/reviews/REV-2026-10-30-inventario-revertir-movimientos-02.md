# REV-2026-10-30-inventario-revertir-movimientos-02: Cobertura incompleta de concurrencia y de «sin rol» en la reversión de recepciones

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-30-inventario-revertir-movimientos.md (v1)
**Spec reference:** AC-13, AC-09; Test Specification (Concurrencia, orden de bloqueos compra → almacén); Risks
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
(1) El único test de concurrencia de `RevertReception` usa `FakeStock(enabled=False)` (recepción documental): no ejercita el orden de bloqueos compra → almacén contra el libro real, que el plan señala como riesgo principal (p. ej. reversión simultánea de una recepción de inventario o contra una nueva recepción de la misma compra). (2) El mapeo AC-13 promete prueba «sin rol/módulo»; solo hay pruebas de módulo deshabilitado y de otra empresa, no de usuario sin empresa/rol.

## Expected behavior
Un test con conexiones reales sobre una recepción en modo inventario (dos reversiones simultáneas, un ganador, un único juego de contramovimientos) y un test de 403 para usuario autenticado sin rol admin/empresa en ambos endpoints.

## Actual behavior
La lógica revisada es correcta (compra bloqueada con `for_update` antes de `locked(warehouse)`, igual que `RegisterReception`), pero el orden de bloqueos con el libro real y el 403 por rol no tienen prueba. Las suites existentes pasan.

## Evidence
- `backend/modules/purchases/tests/test_receipt_revert.py` clase `ReceiptRevertConcurrencyTests` (usa `FakeStock(enabled=False)`).
- `backend/modules/inventory/tests/test_reversal.py` `ReverseSourceConcurrencyTests` prueba solo el caso de uso de Inventario, no el flujo compra → almacén.
- Búsqueda de 403 por rol en ambos archivos: solo hay 403 por módulo deshabilitado.
