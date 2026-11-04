# REV-2026-11-04-refinar-ux-pedidos-ventas-02: openPayment y foco inicial usan setTimeout sin cancelar y acoplan por id/DOM

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-04-refinar-ux-pedidos-ventas.md (v1)
**Spec reference:** AC-02, AC-07; CLAUDE.md (frontend: sin suscripciones/recursos colgados, lógica no visual en services)
**Plan mode:** COMPACTO
**Suggested owner:** frontend (features/sales)

## Description
- `OrderDetailComponent.openPayment()` hace `scrollIntoView` y `setTimeout(() => host?.querySelector('#payment-amount')?.focus())` buscando por id un campo interno del hijo `app-order-payments`.
- `OrderItemsComponent` (effect) lanza `setTimeout(() => select.focus())` una sola vez.

## Expected behavior
Foco/scroll sin timers sueltos ni dependencia de ids internos del hijo (p. ej. que `OrderPaymentsComponent.open()` enfoque su propio campo con `afterNextRender`).

## Actual behavior
Funciona y está cubierto por pruebas fakeAsync, pero los timers no se cancelan si el componente se destruye antes del tick (riesgo mínimo: optional chaining protege el acceso) y renombrar `#payment-amount` rompería el foco en silencio (no hay prueba que lo verifique).

## Evidence
order-detail.component.ts (`openPayment`), order-items.component.ts (effect de foco), order-payments.component.html línea 12-13 (`id="payment-amount"`).
