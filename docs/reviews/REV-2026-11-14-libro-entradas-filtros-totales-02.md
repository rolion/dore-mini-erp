# REV-2026-11-14-libro-entradas-filtros-totales-02: RecordedEntry no coincide con la forma declarada en API-03 y no está en Desviaciones

**Status:** Resolved
**Severity:** Low
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-11-14-libro-entradas-filtros-totales.md (v1)
**Spec reference:** API-03
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
API-03 y el plan declaran `services.record_entry(company_id, EntryInput) -> RecordedEntry{entry, created}`. La implementación devuelve un DTO plano `RecordedEntry(entry_id, account_id, currency, amount, payment_date, created)`.

## Expected behavior
O bien el retorno coincide con el contrato, o la diferencia figura en «Desviaciones» del TASK (las 5 declaradas no la mencionan) y se actualiza API-03 antes de que PB-ACC-003/PB-COB-002 consuman el contrato.

## Actual behavior
Forma distinta y sin declarar. Funcionalmente suficiente (id, cuenta, moneda, monto, fecha y `created`), y coherente con el patrón de DTO inmutable de `AccountRef`.

## Evidence
`backend/modules/accounting/services.py`: `class RecordedEntry: entry_id, account_id, currency, amount, payment_date, created`; `return RecordedEntry(stored.id, stored.account_id, ...)`. Los tests usan `result.entry_id` / `result.created`.

## Resolution
`record_entry` devuelve `RecordedEntry{entry: EntryRef, created}` como declara API-03 (la implementación se alineó con la Specification; no hay cambio de contrato). Tests actualizados a `result.entry.id`.
