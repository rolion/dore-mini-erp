# REV-2026-10-08-ciclo-pedido-entrega-cobro-01: XSS almacenado por el nombre de producto en el diálogo "Quitar ítem"

**Status:** Closed
**Severity:** High
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-08-ciclo-pedido-entrega-cobro.md (v1)
**Spec reference:** Non-functional requirements → Seguridad ("`reason`/`notes` se escapan en la UI (no `innerHTML`/`Swal html` sin escapar)"); AC-25 (quitar con confirmación)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-engineer

## Description
`OrderDetailComponent.confirmRemove` arma el título del diálogo SweetAlert2 con el nombre del producto sin escapar:
`frontend/panel_admin/src/app/features/sales/pages/order-detail/order-detail.component.ts:198`

```ts
title: `¿Quitar "${item.productName}"?`,
```

En SweetAlert2 11.x el parámetro `title` se interpreta como **HTML** (`parseHtmlToContainer(params.title, ...)`); para texto plano existe `titleText`. `productName` es un dato libre del catálogo (snapshot del nombre) que cualquier usuario autenticado puede definir al crear/editar un producto, así que un nombre con HTML se ejecuta en el navegador de quien intente quitar ese ítem de un pedido.

## Expected behavior
La Specification (NFR Seguridad) exige que los textos de usuario se escapen en la UI y que no se use `Swal html` sin escapar. El nombre del producto debe mostrarse como texto, nunca interpretarse como HTML. (El resto de diálogos revisados — entrega, cancelación y duplicados de `customer-quick-create` — usan `text` o `escapeHtml`, y las plantillas Angular escapan por defecto.)

## Actual behavior
Con un producto llamado `<img src=x onerror="window.__xssProbe=1">` el diálogo ejecuta el `onerror`.

## Evidence
Spec temporal (ya eliminado) ejecutado con Karma/ChromeHeadless con la misma construcción de `title`:

```
Swal.fire({ title: `¿Quitar "<img src=x onerror=\"window.__xssProbe=1\">"?` });
...
LOG: 'XSS_PROBE=1'
TOTAL: 1 SUCCESS
```

Fuente de la librería (`node_modules/sweetalert2/dist/sweetalert2.js`, v11.26.25):
```
1897    if (params.title) {
1898      parseHtmlToContainer(params.title, title);
```
Los specs existentes (`order-detail.component.spec.ts`) espían `confirmRemove` y por eso no detectan el problema.

## Required action
Mostrar el nombre como texto (`titleText`/`text`, o escapar con la utilidad `escapeHtml` ya existente) y añadir un spec que verifique que un nombre con HTML no llega como HTML a `Swal.fire`.

## Resolution (re-review 2026-10-09, `3b55ffc`)
Cerrado. `confirmRemove` usa `titleText` (también `customer-list`/`customer-detail`); no quedan `title:` con datos interpolados en la app. Verificado en la UI real con un producto llamado `<img src=x onerror="window.__xss=1">Pan`: el diálogo muestra el texto literal, `window.__xss` queda `undefined` y no hay `<img>` en `.swal2-title`. Specs nuevos en `order-detail`, `customer-list` y `customer-detail`.
