# REV-2026-10-08-ciclo-pedido-entrega-cobro-02: la búsqueda remota de clientes se rompe al seleccionar (TypeError `null.trim()`) y deja el selector cargando

**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-08-ciclo-pedido-entrega-cobro.md (v1)
**Spec reference:** AC-24 (selector de cliente con búsqueda remota), AC-23 (filtro por cliente en la lista), UI-02, EDGE-12 (errores de red → `toastr`)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-engineer

## Description
`CustomerOptionsService.search(term: string)` hace `term.trim()` (`frontend/panel_admin/src/app/features/sales/services/customer-options.service.ts:17`), pero `ng-select` emite `null` por el `typeahead` al seleccionar/limpiar. La excepción se lanza de forma síncrona dentro del `switchMap` (antes de que exista el observable, por lo que el `catchError` interno no la atrapa) y termina el stream de `customers$`: el selector queda con `customersLoading = true` (spinner permanente) y **ya no vuelve a buscar** hasta recargar la página. El mismo patrón está en `order-form.component.ts:72-76` y `order-list.component.ts:111-115` (la lista no se ejercitó por separado en el humo).

## Expected behavior
Seleccionar un cliente deja el selector en reposo, y se puede volver a buscar otro (AC-24: "elegir cliente activo (o 'Sin cliente')" con búsqueda remota; el plan además declara que los fallos no deben romper el selector).

## Actual behavior
Humo manual en `/sales/orders/new` (backend + `ng serve` propios, BD desechable):
1. Abrir el selector, escribir "Ana", esperar 2 s, elegir "Ana Perez".
2. Consola: `ERROR TypeError: Cannot read properties of null (reading 'trim')` en `CustomerOptionsService.search`.
3. El spinner de `ng-select` permanece (`.ng-spinner-loader` presente) con el cliente ya elegido.
4. Reabrir y escribir "Zzz": **no se emite** ninguna petición `GET /api/customers/?search=Zzz` (el stream murió).

## Evidence
```
[error] ERROR TypeError: Cannot read properties of null (reading 'trim')
    at _CustomerOptionsService.search (sales.routes-*.js)
    at _OrderFormComponent.searchCustomers (sales.routes-*.js)
hook de console.error -> ["ERROR TypeError: Cannot read properties of null (reading 'trim')"] | spinner=true | value=Ana Perez
```
Peticiones tras reabrir y teclear "Zzz": ninguna `?search=Zzz` (la última fue `?search=Ana`). Los specs no lo detectan porque emiten solo `string` en el `Subject` de `typeahead`.

## Required action
Tolerar `null`/`undefined` en el término (p. ej. `term ?? ''` en el servicio o en el `switchMap`), proteger el stream para que un error no lo termine, y añadir specs que emitan `null` por `customerInput$` en el formulario y en la lista.
