# REV-2026-11-03-agendar-y-gestionar-citas-10: Búsqueda de clientes del formulario sin cancelar respuestas anteriores

**Status:** Verified
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-03-agendar-y-gestionar-citas.md (v1)
**Spec reference:** CLAUDE.md (Frontend: sin suscripciones colgadas, lógica en servicios); AC-09
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`AppointmentFormComponent.searchCustomers` suscribe una petición nueva por cada término (tras debounce) sin `switchMap`: una respuesta lenta de un término anterior puede sobrescribir `customers` con resultados desactualizados. Además, al cambiar la búsqueda la lista se reemplaza y el cliente ya elegido (`customer_id`) puede dejar de estar entre las opciones, por lo que el `select` se ve vacío aunque el formulario conserve el id.

## Expected behavior
Solo cuenta la última búsqueda y el cliente seleccionado sigue visible.

## Actual behavior
Posible orden de respuestas inverso y selección que parece perdida.

## Evidence
appointment-form.component.ts: `this.customerSearch.valueChanges.pipe(debounceTime(300), ...).subscribe(term => this.searchCustomers(term))` y `searchCustomers` hace `.subscribe` interno; `customers = page.results` sin conservar el elegido.

## Resolución
La búsqueda de clientes usa `switchMap` (descarta respuestas anteriores) y el cliente elegido se conserva entre las opciones. Spec en `appointment-form.component.spec.ts`.

## Verificación (Quality Gate 3)
Verificado en gate 3: `switchMap` en la búsqueda (`merge(of(''), valueChanges.pipe(debounceTime(300)))` con `catchError` interno, el flujo no muere ante un error) y `selectedCustomer` conservado vía `showCustomers`. Spec `only the latest customer search counts…` comprueba `first.cancelled` y que `customers` = [elegido, resultado]. En el navegador: con «Rosa Pérez» elegida, buscar «car» deja las opciones «Rosa Pérez» (conservada) y «Carlos Quispe» y el select sigue en Rosa; al limpiar la búsqueda vuelve la lista completa sin duplicar a Rosa y la selección se mantiene.
