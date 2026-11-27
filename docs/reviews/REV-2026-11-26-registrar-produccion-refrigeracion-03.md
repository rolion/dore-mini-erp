# REV-2026-11-26-registrar-produccion-refrigeracion-03: Pantalla de registro usa tarjetas y colapsa errores por linea

**Status:** Resolved
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-26-registrar-produccion-refrigeracion.md
**Spec reference:** AC-11, DDR (tabla Ingredientes, error por campo)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El DDR describe una tabla Ingredientes con Previsto y Consumo real; la pantalla usa tarjetas en todos los anchos. Los errores 400 por linea (ingredients[].actual_quantity) se unen en un solo texto sobre la lista en vez de marcar la fila. El costo se muestra como cadena cruda sin formato.

## Expected
Tabla en escritorio / tarjetas en movil, errores en la fila, costo formateado.

## Actual
order-refrigerate.component.html usa ul.line-cards siempre; orders-api.service.ts ingredientsText() une mensajes; order-detail muestra order.costTotal sin formato.

## Evidence
Revision por lectura de codigo; no se inspecciono en navegador.

## Resolución
Errores por línea marcados en su fila (`ingredientLines`, `data-testid="line-server-error"`) y costo con el pipe `money` en el detalle; con specs. **Desviación aceptada:** la pantalla de registro mantiene tarjetas en todos los anchos (no tabla en escritorio); es Low y queda como deuda de diseño.
