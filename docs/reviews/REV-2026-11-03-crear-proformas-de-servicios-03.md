# REV-2026-11-03-crear-proformas-de-servicios-03: La prueba de AC-04 no distingue el rechazo por cliente inactivo o ajeno

**Status:** Resolved (pendiente de re-verificación con PostgreSQL)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-03-crear-proformas-de-servicios.md (v1)
**Spec reference:** AC-04; Test Specification (cliente/servicio inactivos o ajenos)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
En `test_inactive_or_foreign_service_and_customer_are_rejected` (`backend/modules/quotations/tests/test_api.py`), el servicio `corona` se desactiva al inicio. Las dos comprobaciones de cliente (inactivo y ajeno) usan el payload por defecto, que incluye esa línea de `corona`.

## Expected behavior
Cada comprobación aísla una sola causa: con líneas válidas, un cliente inactivo o ajeno devuelve 400 con `customer_id`.

## Actual behavior
Ambas aserciones devuelven 400 aunque la validación del cliente estuviera rota, porque la línea de `corona` ya es inválida. Además, las aserciones solo miden el código de estado, no la clave del error (`lines` frente a `customer_id`). La prueba pasaría con la regla de cliente eliminada. Es una debilidad de la prueba; la lógica de `_customer` es correcta por lectura.

## Evidence
`test_api.py`: `ServiceModel.objects.filter(pk=self.corona.pk).update(active=False)` seguido de `CustomerModel...update(active=False)` y `self.assertEqual(self.create().status_code, 400)`, con líneas por defecto `[limpieza, corona]`. Prueba con BD no ejecutada.
