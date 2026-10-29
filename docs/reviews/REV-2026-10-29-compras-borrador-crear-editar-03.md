# REV-2026-10-29-compras-borrador-crear-editar-03: falta test_adapters.py del PLAN y no hay prueba del bloqueo de fila fuera de transacción

**Status:** Fixed (pendiente de reverificar en el ciclo 2)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-29-compras-borrador-crear-editar.md (v1)
**Spec reference:** Test Specification → Integration tests (`purchases/tests/test_adapters.py`), Risks (concurrencia)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El PLAN lista `purchases/tests/test_adapters.py` (adaptador `ProductCatalog` sobre la fachada real). No existe en el diff ni en `backend/modules/purchases/tests/`; el adaptador solo se ejercita indirectamente vía `test_purchase_api`. Además, todos los tests de API corren dentro de `TestCase` (transacción abierta) sobre SQLite, por lo que ninguna prueba habría detectado REV-01.

## Expected behavior
Existe una prueba directa del adaptador y una prueba que falle si una mutación del borrador intenta bloquear la fila sin transacción (patrón de `sales/tests/test_repository.py::LockingOutsideTransactionTests`).

## Actual behavior
El archivo del PLAN no se entregó y la omisión no está declarada en `## Implementación` del TASK («Desviaciones respecto al plan: ninguna de alcance»).

## Evidence
`ls backend/modules/purchases/tests` → `test_api.py test_application.py test_domain.py test_purchase_api.py test_purchase_application.py test_purchase_domain.py test_purchase_repository.py test_services.py` (sin `test_adapters.py`). `git diff --stat origin/main...HEAD` no lo incluye.
