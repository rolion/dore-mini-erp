# REV-2026-11-16-configurar-asientos-automaticos-modulo-01: post_automatic_entry no es idempotente si la configuración cambió entre el intento y el reintento

**Status:** Resolved
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-16-configurar-asientos-automaticos-modulo.md (v1)
**Spec reference:** AC-09, INV-04, AC-05
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
post_automatic_entry (backend/modules/accounting/services.py, bloque «Asientos automáticos por evento») evalúa cobertura y resuelve la configuración ANTES de consultar si el evento ya tiene asiento. Un reintento del mismo (evento, origin_id) tras cambiar o quitar la configuración ya no es un reintento idempotente.

## Expected behavior
Repetir un evento ya contabilizado devuelve el asiento existente (created=False) aunque la configuración haya cambiado después (INV-06: cambiar la configuración no afecta lo ya contabilizado), o al menos no lanza error por configuración posterior.

## Actual behavior
Con el asiento ya creado: (a) si el método CASH pasó de Banco a Caja, el reintento lanza JournalConflict («El evento ya tiene un asiento con otros datos: lines»); (b) si se quitó la cuenta del rol RECEIVABLE, el reintento lanza PostingConfigurationMissing aunque el asiento exista.

## Evidence
Sonda temporal (ya eliminada, sin cambios en el árbol) sobre PostingBase:
RETRY1 RAISED JournalConflict El evento ya tiene un asiento con otros datos: lines.
RETRY2 RAISED PostingConfigurationMissing Falta configurar la cuenta «Cuentas por cobrar». Configúrela en Ventas › Configuración › Asientos automáticos.
test_posting_service.py::test_repeating_the_event_creates_one_entry_and_a_different_one_conflicts solo repite con la configuración sin cambios. Sugerencia: consultar get_by_origin(definition.code, origin_id) antes de resolver y devolver created=False si existe (conservando el conflicto solo si cambian importe/fecha).

## Resolution
`post_automatic_entry` consulta `get_by_origin` antes de la cobertura y la configuración y devuelve el asiento existente (`created=False`); solo conserva el conflicto si cambian fecha o importe. Prueba: `test_a_retry_after_the_configuration_changed_still_returns_the_existing_entry`.
