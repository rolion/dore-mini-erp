# REV-2026-10-08-ciclo-pedido-entrega-cobro-03: un producto con precio 0 es seleccionable pero no se puede agregar al pedido

**Status:** Open
**Severity:** Low
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-10-08-ciclo-pedido-entrega-cobro.md (v1)
**Spec reference:** INV-01 ("precio de ítem y monto de pago > 0"), AC-03; deriva de Catalog (`sale_price` ≥ 0 permitido)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-plan

## Description
El engineer declaró la desviación: INV-01 exige precio de ítem > 0, pero el catálogo acepta `sale_price = 0` (muestras, obsequios). Un producto así aparece en el selector del detalle del pedido (`Galleta gratis · Bs 0.00`) y al agregarlo la API responde 400 `product_id` ("El producto no tiene un precio de venta mayor a cero."). La implementación cumple INV-01 tal como está escrita, pero la Specification es incoherente con Catalog y el selector ofrece una opción que siempre falla.

## Expected behavior
Decisión explícita de negocio vía `delivery-plan`: (a) permitir precio 0 en ítems (ajustando INV-01/AC-03 y el cálculo de `PAID` con total 0), o (b) mantener la regla, filtrar/avisar en el selector de producto y documentarlo en el plan.

## Actual behavior
```
POST /api/orders/{id}/items/ {"product_id": "<producto con precio 0>", "quantity": 1}
-> 400 {"product_id": ["El producto no tiene un precio de venta mayor a cero."]}
```

## Evidence
Salida real del comando anterior contra el backend de revisión; captura del selector con "Galleta gratis · Bs 0.00" disponible. No bloquea el PR por sí misma (severidad Low); queda registrada para decisión del usuario.
