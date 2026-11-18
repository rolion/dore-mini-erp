# REV-2026-11-18-consultar-flujo-dinero-contabilidad-04: Detalles menores: orden de desempate y texto del design-system

**Status:** Resolved (corregido en el commit siguiente; pendiente de reconfirmar en el próximo Quality Gate)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-18-consultar-flujo-dinero-contabilidad.md (v1)
**Spec reference:** Edge cases (orden estable); design-system §6
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
1. La Specification pide orden estable «fecha contable ↓, created_at ↓, id ↓, cuenta»; `ListCashFlowMovements` usa `reverse=True` sobre toda la tupla, por lo que cuenta y clase también quedan descendentes.
2. `docs/design/design-system.md` §6 dice «suma el submenú Flujo de dinero y tiene cuatro submenús» (ahora son cinco con Flujo de dinero; redacción inconsistente).
3. `cash-flow.component.scss` usa valores HEX solo como fallback de `var(--bs-*)` (bajo riesgo).

## Expected behavior
Desempate por cuenta ascendente; texto coherente.

## Actual behavior
Ver arriba. Sin impacto funcional en totales.

## Evidence
`application/cash_flow.py` líneas de `sorted(..., reverse=True)`; `docs/design/design-system.md` línea del submenú Contabilidad.
