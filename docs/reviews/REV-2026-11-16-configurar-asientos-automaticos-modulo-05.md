# REV-2026-11-16-configurar-asientos-automaticos-modulo-05: Contrato API-01 difiere de la Specification y mensajes de faltantes solo en español

**Status:** Open
**Severity:** Low
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-11-16-configurar-asientos-automaticos-modulo.md (v1)
**Spec reference:** API-01, AC-14
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
La respuesta real de GET posting-config no coincide con la forma declarada en API-01 y el plan no se actualizó (Changelog solo v1).

## Expected behavior
Respuesta conforme a API-01: events[].issues[{code, role, label, message}], events[].preview[{side, label, account_label, status}], roles[].shared_with como lista de módulos.

## Actual behavior
Se devuelve issues[{code, role, subject, module, message}], preview[{side, role, label, account{id,code,name,is_active}|null, status}] y shared_with[{module, label}]; además module_label. El frontend es coherente con la forma real, por lo que no hay fallo funcional, pero el contrato documentado quedó desactualizado. Además, los mensajes de issues/row.issue vienen del backend en español y se muestran sin traducir a usuarios en/pt (p. ej. «Falta la cuenta Caja o Banco de este método.»).

## Evidence
curl GET /api/accounting/posting-config/?module=sales -> {"module":"sales","module_label":"Ventas",...,"issues":[{"code":"role_unconfigured","role":"RECEIVABLE","subject":"Cuentas por cobrar","module":"sales","message":"Falta configurar la cuenta ..."}]}. Actualizar API-01 (o el plan v2) y decidir si los mensajes se traducen por código en el frontend.
