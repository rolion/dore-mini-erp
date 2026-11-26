# REV-2026-11-25-numeracion-correlativa-pedidos-venta-04: El aviso de período cerrado no muestra el nombre del período (desviación del DDR)

**Status:** Resolved
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-25-numeracion-correlativa-pedidos-venta.md (v1)
**Spec reference:** UI-03; DDR-numeracion-correlativa-pedidos-venta-codigo-y-bloqueo («El período fiscal «{nombre}» está cerrado…»)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El DDR describe el aviso de período cerrado con el nombre del período («El período fiscal «{nombre}» está cerrado…»). El 409 ya envía `{period: <nombre>}` (`OrderNumberingAdapter`, `extra={'period': exc.name}`), pero `app-fiscal-period-alert` solo recibe el código y muestra el texto genérico `SALES.FISCAL_PERIOD.CERRADO` («El período fiscal de la fecha del pedido está cerrado…»).

## Expected behavior
Según el DDR, el aviso nombra el período cerrado (o, si se decide omitirlo, el DDR/TASK debe registrar la desviación).

## Actual behavior
Texto genérico sin nombre; la desviación no figura en «Desviaciones respecto al plan» del TASK. Impacto de UX menor: el mensaje sigue explicando el motivo y la acción (reabrir en Contabilidad).

## Evidence
- `fiscal-period-alert.component.ts`: `input.required<FiscalPeriodErrorCode>()` y `messageKey()` sin parámetros; `es.json`: `"CERRADO": "El período fiscal de la fecha del pedido está cerrado, por eso no se puede confirmar. Reábralo en Contabilidad."`.

## Resolución
Resuelto: `OrderRuleError.periodName` (del `period` del 409), `app-fiscal-period-alert` con `periodName` y clave `SALES.FISCAL_PERIOD.CERRADO_NOMBRE` en es/en/pt; pruebas del componente, del detalle y del servicio.
