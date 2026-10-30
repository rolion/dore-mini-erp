# REV-2026-10-29-compras-borrador-crear-editar-01: PATCH /api/purchases/{id}/ usa select_for_update fuera de una transacción (500 en PostgreSQL)

**Status:** Fixed (pendiente de reverificar en el ciclo 2)
**Severity:** High
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-29-compras-borrador-crear-editar.md (v1)
**Spec reference:** AC-07, ADR modelo-compra-borrador (decisión 5: «`atomic` + `select_for_update` de la compra al editar»), NFR «Guardado atómico»
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`UpdatePurchase.execute` llama a `self.purchases.get(purchase_id, for_update=True)` (`backend/modules/purchases/application/purchase_commands.py:89`). El repositorio aplica `select_for_update()` (`purchase_repository.py::get`) y solo `save()` está decorado con `@transaction.atomic`. La vista `PurchaseDetailView.patch` (`api/purchase_views.py`) ejecuta el caso de uso con `_run(...)` sin envolver en `transaction.atomic()`, y no existe `ATOMIC_REQUESTS` en `config/settings`. El `SELECT ... FOR UPDATE` corre entonces en modo autocommit. En PostgreSQL, Django lo rechaza con `TransactionManagementError`. En SQLite (`has_select_for_update=False`) y dentro de `TestCase` (que abre una transacción) el problema queda oculto. El patrón correcto ya existe en `expenses/api/views.py::_run` (`with transaction.atomic()` para mutaciones).

## Expected behavior
`PATCH /api/purchases/{id}/` actualiza el borrador (200) en PostgreSQL, con la fila bloqueada durante la lectura-modificación-escritura (cabecera y líneas en una sola transacción).

## Actual behavior
En PostgreSQL, todo `PATCH` (la edición del borrador: AC-07, AC-08, AC-16, AC-18) fallaría con un 500 (`TransactionManagementError: select_for_update cannot be used outside of a transaction`). No pude ejecutar PostgreSQL; la reproducción es a nivel de repositorio simulando la capacidad de PostgreSQL.

## Evidence
Entorno sin `DATABASE_URL` ni PostgreSQL; script con SQLite desechable y `has_select_for_update` forzado a `True` (la misma comprobación que hace Django con PostgreSQL), conexión en autocommit como en la vista:

```
autocommit = True
TransactionManagementError select_for_update cannot be used outside of a transaction.
```
(llamada: `DjangoPurchaseRepository(uuid4()).get(uuid4(), for_update=True)`). `grep -rn ATOMIC backend/config` no devuelve nada; `grep atomic backend/modules/purchases` solo encuentra `purchase_repository.py` en `save`.

Corrección sugerida: envolver la ejecución de las mutaciones de la vista en `transaction.atomic()` (como `expenses`), añadir una prueba que falle si se bloquea sin transacción (como `sales/tests/test_repository.py::LockingOutsideTransactionTests`) y reverificar contra PostgreSQL.
