# REV-2026-11-15-conciliar-regularizar-pagos-historicos-02: La tabla «casos a revisar» muestra la fecha en formato ISO en vez de dd/MM/yyyy

**Status:** Resolved
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-14-conciliar-regularizar-pagos-historicos.md (v2)
**Spec reference:** UI-03; design-system.md §8 («fechas dd/MM/yyyy»)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-frontend

## Description
`regularization.component.html` pinta `{{ detail.paymentDate }}` sin el pipe `date`; la API devuelve `2026-03-05`. Las pantallas hermanas del libro usan `| date: 'dd/MM/yyyy'`.

## Expected behavior
`{{ detail.paymentDate | date: 'dd/MM/yyyy' }}` (checklist §8 de `docs/design/design-system.md`).

## Actual behavior
La fecha se muestra como `AAAA-MM-DD`; inconsistente con Entradas.

## Evidence
- `features/accounting/pages/regularization/regularization.component.html`: `<td>{{ detail.paymentDate }}</td>`.
- `features/accounting/pages/entry-list/entry-list.component.html:137`: `{{ row.paymentDate | date: 'dd/MM/yyyy' }}`; `entry-detail.component.html:35` igual.

## Resolución
La fecha de los casos a revisar usa `| date: 'dd/MM/yyyy'`. Spec: `shows the payment date of the cases to review as dd/MM/yyyy`; verificado en el navegador (02/11/2026).
