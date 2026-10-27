# REV-2026-10-27-configuracion-por-modulo-y-empresa-01: El fallback de SalesSettingsAdapter no funciona ante errores de base de datos dentro de la transaccion

**Status:** Resolved
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-27-configuracion-por-modulo-y-empresa.md (v1)
**Spec reference:** EDGE-06, AC-07
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`SalesSettingsAdapter.max_discount_percent` (backend/modules/sales/infrastructure/adapters.py) captura `Exception` y devuelve 100. Se ejecuta dentro de `transaction.atomic()` (sales/api/views.py `_run`, con select_for_update).

## Expected behavior
Si la lectura de configuracion falla, Ventas usa el valor inicial y el descuento se aplica como antes (EDGE-06).

## Actual behavior
Solo cubre errores de Python (el test usa mock.patch con RuntimeError). Si la falla es de base de datos (DatabaseError, tabla inexistente, conexion), PostgreSQL deja la transaccion abortada: el `except` la traga, pero el siguiente `repository.save` falla con TransactionManagementError/InternalError y la API responde 500. El `except Exception` tan amplio ademas oculta errores de programacion. El propio TASK lo declara como deuda tecnica.

## Evidence
Lectura de adapters.py lineas 47-59 y de sales/api/views.py (_run con atomic). test_settings_read_failure_falls_back_to_initial_rule usa mock (sales/tests/test_api.py). Sugerencia: leer la configuracion fuera de la transaccion/antes de abrirla, o envolver la lectura en un savepoint (transaction.atomic anidado) y acotar la excepcion a DatabaseError; agregar un test con fallo real de BD.

## Resolution
Corregido: la lectura corre en un savepoint (`transaction.atomic()` en `SalesSettingsAdapter`); test `test_database_error_reading_settings_does_not_break_the_request` (falla sin el savepoint con `InternalError`).
