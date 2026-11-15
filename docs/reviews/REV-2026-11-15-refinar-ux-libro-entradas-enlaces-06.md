# REV-2026-11-15-refinar-ux-libro-entradas-enlaces-06: El enlace al cobro no funciona con datos reales de servicios

**Status:** Deferred
**Severity:** High
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-11-15-refinar-ux-libro-entradas-enlaces.md (v1)
**Spec reference:** AC-01, AC-02
**Plan mode:** COMPACTO
**Suggested owner:** delivery-start

## Description
`sourceLink` espera `documentRef = <kind>/<number>` para servicios, pero el backend guarda solo el número de la proforma. Con datos reales el enlace a Cobros (y el ya existente de Documento) nunca se genera.

## Expected behavior
Con un cobro de servicios disponible, Comprobante (`CB-…`) y Documento enlazan a `/pocketbiz/receivables/<kind>/<number>`.

## Actual behavior
`document_ref` de servicios = `ODO-000002` (sin `kind/`): `sourceLink` devuelve `null`, se muestra texto. Es lo que se ve en las capturas de la persona (ODO-000002 sin enlace). Las pruebas y la verificación visual simulada usaban `quotation/PRO-1`, que no es lo que produce el backend.

## Evidence
- `backend/modules/receivables/infrastructure/adapters.py:67`: `origin_document_ref=number` (el `kind` llega a `record(kind, number, ...)` pero no se guarda).
- `backend/modules/accounting/api/serializers.py:90`: `document_ref` se expone tal cual; no hay `kind`.
- `frontend/.../accounting/models/entry.ts:129-130`: `const [kind, number] = documentRef.split('/')` → `null` si no hay `/`.
- Posibles salidas (decisión de contrato/datos, requiere aprobación): (a) el backend guarda `kind/number` + migración de datos de filas existentes; (b) la API de entradas expone `source.kind` sin tocar lo guardado (hay que resolver el `kind` de filas existentes); (c) el frontend asume un único `kind` (frágil).

## Resolution
Por instrucción de la persona, la liga hacia el cobro se omite por ahora (PLAN v2): se retiró el enlace de Comprobante y el botón «Ver cobro». La decisión de contrato/datos (A/B/C) queda pendiente para una tarea posterior.
