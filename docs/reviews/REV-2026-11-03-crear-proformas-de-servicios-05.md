# REV-2026-11-03-crear-proformas-de-servicios-05: El formulario envía siempre `unit_price` de las líneas nuevas, con el precio del catálogo cargado al abrir

**Status:** Resolved (pendiente de re-verificación con PostgreSQL)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-03-crear-proformas-de-servicios.md (v1)
**Spec reference:** INV-02 (se copian nombre y precio vigentes al incorporar la línea); AC-03
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`proforma-form.component.ts` rellena `unit_price` con `service.basePrice`, leído al abrir el formulario (`pickService`), y `submit()` lo envía para toda línea nueva aunque el usuario no lo haya editado.

## Expected behavior
Si el usuario no modificó el precio de una línea nueva, se omite `unit_price` y el servidor captura el precio vigente en ese momento (INV-02).

## Actual behavior
Si el precio cambia en el catálogo con el formulario abierto, un administrador congela el precio viejo sin aviso. Un rol futuro sin permiso de precio recibiría un 403 incomprensible, porque el valor enviado difiere del vigente. Hoy solo existe el rol admin, así que el impacto es bajo.

## Evidence
`proforma-form.component.ts`: `unit_price: String(line.unit_price)` en el mapeo de `submit()`, sin distinguir si el control se modificó (`dirty`). `pickService` hace `patchValue({ unit_price: service.basePrice })`.
