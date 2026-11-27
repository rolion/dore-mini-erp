# REV-2026-11-26-numeracion-correlativa-compras-02: La alerta compartida de período habla de «pedido» también en el detalle de una compra

**Status:** Resolved
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-26-numeracion-correlativa-compras.md (v1)
**Spec reference:** AC-13, UI-03 (el 409 de período se explica en `alert-warning`; textos en es/en/pt); DDR «Bloqueo al confirmar»
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build (frontend)

## Description
Al mover `app-fiscal-period-alert` a `shared/components` solo se renombraron las claves (`SALES.FISCAL_PERIOD.*` → `COMMON.FISCAL_PERIOD.*`); los textos siguen redactados para pedidos de venta («La fecha del pedido…», «The order date…», «A data do pedido…»). El detalle de compras usa ese mismo componente, así que el aviso de una compra bloqueada habla de un pedido.

## Expected behavior
El texto que ve el usuario al confirmar una compra bloqueada se refiere a la compra (o es neutro, p. ej. «la fecha del documento» / parámetro `{{kind}}` o claves por módulo), en es, en y pt.

## Actual behavior
En el detalle de una compra con 409 `fiscal_period_missing` se muestra: «La fecha del pedido no está dentro de ningún período fiscal, por eso no se puede confirmar…» (es), «The order date is not inside any fiscal period…» (en), «A data do pedido não está dentro…» (pt); igual para `CERRADO` y `CERRADO_NOMBRE`.
Menor, en el mismo bloque: el JSON movido a `COMMON.FISCAL_PERIOD` quedó con sangría de 4 espacios para las claves hijas (las demás claves de `COMMON` usan 4 y los hijos de un objeto 6), en `es.json`, `en.json` y `pt.json` (solo estética, `i18n:check` no lo detecta).

## Evidence
`frontend/panel_admin/src/assets/i18n/es.json` líneas 176-181:
```
"FISCAL_PERIOD": {
"SIN_PERIODO": "La fecha del pedido no está dentro de ningún período fiscal, por eso no se puede confirmar. Cree el período en Contabilidad.",
"CERRADO": "El período fiscal de la fecha del pedido está cerrado, ...
```
`purchase-detail.component.html`: `<app-fiscal-period-alert [code]="fiscalPeriodError" [periodName]="fiscalPeriodName" />` (sin forma de cambiar el sustantivo). Revisión por código; la revisión visual en navegador no se hizo.

## Resolución
Resuelto: textos del componente compartido neutros en es/en/pt (ya no dicen «pedido»; hablan de «la fecha») y bloque `COMMON.FISCAL_PERIOD` con indentación coherente; componente, detalle de compras y de ventas verificados por Karma.
