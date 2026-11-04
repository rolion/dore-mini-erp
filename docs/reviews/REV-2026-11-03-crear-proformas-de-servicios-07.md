# REV-2026-11-03-crear-proformas-de-servicios-07: Huecos de cobertura frente al mapeo de pruebas del PLAN

**Status:** Resolved (pendiente de re-verificación con PostgreSQL y revisión visual)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-03-crear-proformas-de-servicios.md (v1)
**Spec reference:** Test Specification (Integration tests, Acceptance criteria mapping AC-06, AC-10, AC-11, Edge cases)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Revisión de las pruebas por lectura (las de BD no se ejecutaron). Cubren AC-01..10 en lo principal, pero faltan puntos que el PLAN nombra.

## Expected behavior
- AC-06: conteo de filas sin cambios en `sales` e `inventory` (ventas, cuentas por cobrar, pagos, movimientos).
- AC-10: el módulo `quotations` exige `services` y `customers` para habilitarse.
- AC-11: «specs de servicio/componentes».
- Edge cases: cabecera sin cliente, vigencia anterior a la fecha por API, más de 200 líneas, `id` repetido, 403 también en PUT, y regla de precio sobre líneas congeladas.

## Actual behavior
- AC-06 solo cuenta `OrderModel`; no revisa cuentas por cobrar, pagos ni stock.
- Ninguna prueba cubre la dependencia `requires` de `quotations` (el cambio en `modularity/tests/test_api.py` solo reordena la lista).
- Hay un spec de servicio y el del sidebar, pero ninguno de las tres páginas ni de `previewSubtotal` en el formulario.
- La propiedad «el servidor ignora subtotal/total enviados» está cubierta. El resto de los edge cases listados no tiene prueba de API.
- Observación: `_lines` devuelve solo los errores de servicio y deja para una segunda ronda los de cantidad y precio. No es un incumplimiento.

## Evidence
`test_api.py::test_saving_repeatedly_creates_no_sale_or_stock` cuenta `OrderModel`, `ProformaModel` y `ProformaLineModel`. `modularity/tests/test_api.py` cambia solo el orden esperado de claves. En `frontend/.../features/quotations/` solo existe `services/proformas-api.service.spec.ts`.
