# REV-2026-11-17-reconocer-compras-mercaderia-deuda-proveedores-09: La vista previa del pago no devuelve `account.id` (API-03)

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-17-reconocer-compras-mercaderia-deuda-proveedores.md (v2)
**Spec reference:** API-03 («lines:[{side, role, account:{id,name}|null, amount}]»)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
API-03 define cada línea de `GET /api/purchases/{id}/payments/preview/` con `account: {id, name} | null`. La implementación devuelve solo `account: {name}`: `PaymentPreviewLine` no transporta el id aunque la fachada (`PostingPreviewLine.account_id`) lo expone.

## Expected behavior
`lines[].account` incluye `id` y `name` como dice la Specification (o la Specification se corrige a `{name}`).

## Actual behavior
`account` solo trae `name`; modelo del frontend (`PaymentPreview.lines[].account: { name: string }`) y prueba (`l['account']['name']`) lo asumen así. Sin impacto funcional hoy (la UI solo muestra el nombre).

## Evidence
```
backend/modules/purchases/api/payment_serializers.py (preview_representation):
    'lines': [{'side': line.side, 'role': line.role, 'account': {'name': line.account_name}, 'amount': money(line.amount)} ...]
backend/modules/purchases/infrastructure/adapters.py (preview_payment):
    PaymentPreviewLine(line.side, line.role, line.account_name, line.amount)   # sin account_id
```

## Resolution
Resuelto: se alineó API-03 del PLAN v2 con el contrato implementado (`account: {name}`); el id no lo consume ninguna pantalla.
